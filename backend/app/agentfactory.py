# backend/app/agentfactory.py
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet, ListSortOrder, MessageRole
from .config import PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME, orchestrator_agent_name, orchestrator_instruction, agent_behavior_instructions
from .tools import generate_graph_data, user_functions, execute_databricks_query, get_insights_from_text
import traceback
import json
import time
from datetime import datetime, timedelta

@dataclass
class AgentResponse:
    response: str
    thread_id: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    graph_data: Optional[Dict[str, Any]] = None
    is_error: bool = False
    
    def to_dict(self):
        return {
            "response": self.response,
            "thread_id": self.thread_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "graph_data": self.graph_data,
            "status": "error" if self.is_error else "success"
        }

class AgentFactory:
    def __init__(self):
        self.agent = None
        self.agent_client = AgentsClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            )
        )
        self.current_thread = None
        self.active_runs = {}  # Track active runs by thread_id
        self.last_request_time = {}  # Track last request time by thread_id

    def get_or_create_agent(self) -> str:
        """Returns existing agent ID or creates new one"""
        if self.agent is not None:
            return self.agent.id

        registered_tools = [
            execute_databricks_query,
            get_insights_from_text,
            *([] if generate_graph_data is None else [generate_graph_data]),
        ]

        # Check for existing agent
        existing_agents = list(self.agent_client.list_agents())  
        for agent in existing_agents:
            if agent.name == orchestrator_agent_name:
                print(f"Reusing existing agent: {agent.name} ({agent.id})")
                self.toolset = ToolSet()
                self.toolset.add(FunctionTool(registered_tools))
                self.agent_client.enable_auto_function_calls(self.toolset)
                self.agent = agent
                return self.agent.id

        # Create new agent
        print(f"Creating new agent: {orchestrator_agent_name}")
        self.toolset = ToolSet()
        self.toolset.add(FunctionTool(registered_tools))
        self.agent_client.enable_auto_function_calls(self.toolset)
        
        self.agent = self.agent_client.create_agent(
            model=MODEL_DEPLOYMENT_NAME,
            name=orchestrator_agent_name,
            instructions=orchestrator_instruction,
            toolset=self.toolset,
            top_p=0.01,
            temperature=0.99
        )
        return self.agent.id

    def run_tool(self, tool_name: str, args: dict) -> str:
        """Execute a specific tool by name"""
        for tool in self.toolset._tools:
            if hasattr(tool, "functions"):
                for fn in tool.functions:
                    if fn.__name__ == tool_name:
                        return json.dumps(fn(**args))
        raise ValueError(f"No tool found for name: {tool_name}")

    def process_request2(
        self,
        prompt: str,
        agent_mode: str = "Balanced",
        file_content: Optional[str] = None,
        chat_history: Optional[list] = None,
        thread_id: Optional[str] = None,
        max_retries: int = 3
    ) -> AgentResponse:
        try:
            agent_id = self.get_or_create_agent()
            
            # Check for active runs and clean up old ones
            self._cleanup_stale_runs()
            
            # Get or create thread with active run checking
            thread = self._get_thread_with_retry(thread_id, max_retries)
            if isinstance(thread, AgentResponse):
                return thread  # Return early if we got an error response

            # Prepare full instruction set
            behavior_instruction = agent_behavior_instructions.get(agent_mode, "")
            full_instruction = f"""
                [Orchestrator Instructions]
                {orchestrator_instruction}

                [Behavior Instructions - Mode: {agent_mode}]
                {behavior_instruction}
                """.strip()

            # Initialize thread if new
            if not thread_id:
                self._send_message_with_retry(
                    thread.id,
                    "assistant",
                    full_instruction,
                    max_retries
                )

            # Prepare and send user message
            user_message_content = prompt
            if file_content:
                user_message_content += f"\n\n[FILE_CONTENT_START]\n{file_content}\n[FILE_CONTENT_END]"

            self._send_message_with_retry(
                thread.id,
                "user",
                user_message_content,
                max_retries
            )

            # Track this run as active
            self.active_runs[thread.id] = datetime.now()
            
            # Execute the run
            run = self.agent_client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=agent_id
            )
            
            # Process the results
            return self._process_run_results(
                run,
                thread.id,
                max_retries
            )

        except Exception as e:
            print(f"Exception in process_request2:\n{traceback.format_exc()}")
            error_msg = str(e)
            if "active run" in error_msg.lower():
                error_msg = "Please wait while I finish processing your previous request."
            return AgentResponse(
                response=f"An error occurred: {error_msg}",
                thread_id=thread_id if 'thread' in locals() else None,
                is_error=True
            )

    def _get_thread_with_retry(self, thread_id: Optional[str], max_retries: int):
        """Handle thread retrieval with active run checking"""
        for attempt in range(max_retries):
            try:
                if thread_id:
                    # Check for active runs
                    active_runs = list(self.agent_client.runs.list(
                        thread_id=thread_id,
                        status="in_progress"
                    ))
                    if active_runs:
                        if attempt == max_retries - 1:
                            return AgentResponse(
                                response="Please wait while I finish processing your previous request.",
                                thread_id=thread_id,
                                is_error=False
                            )
                        time.sleep(1 * (attempt + 1))
                        continue
                    
                    return self.agent_client.threads.get(thread_id)
                elif self.current_thread:
                    return self.current_thread
                else:
                    thread = self.agent_client.threads.create()
                    self.current_thread = thread
                    return thread
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1 * (attempt + 1))
                
    def _send_message_with_retry(self, thread_id: str, role: str, content: str, max_retries: int):
        """Send message with retry logic"""
        for attempt in range(max_retries):
            try:
                self.agent_client.messages.create(
                    thread_id=thread_id,
                    role=role,
                    content=content
                )
                return
            except Exception as e:
                if "active run" in str(e) and attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
                raise

    def _process_run_results(self, run, thread_id, max_retries):
        """Process run results with retry logic"""
        prompt_tokens = run.usage.prompt_tokens or 0
        completion_tokens = run.usage.completion_tokens or 0
        
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            return AgentResponse(
                response=f"An error occurred: {run.last_error.message if run.last_error else 'Unknown error'}",
                thread_id=thread_id,
                is_error=True,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens
            )

        # Get messages with retry
        messages = None
        for attempt in range(max_retries):
            try:
                messages = list(self.agent_client.messages.list(
                    thread_id=thread_id,
                    order=ListSortOrder.ASCENDING
                ))
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1 * (attempt + 1))

        # Find agent response
        agent_response = None
        for message in reversed(messages):
            if message.role == MessageRole.AGENT and message.text_messages:
                agent_response = message.text_messages[-1].text.value
                break

        if agent_response is None:
            return AgentResponse(
                response="Agent did not provide a direct response. Check logs for tool outputs.",
                thread_id=thread_id,
                is_error=False,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens
            )

        # Clean up active run tracking
        if thread_id in self.active_runs:
            del self.active_runs[thread_id]

        # Parse response
        try:
            parsed_response = json.loads(agent_response)
            if isinstance(parsed_response, dict) and "graph_data" in parsed_response:
                return AgentResponse(
                    response=parsed_response.get("response", "Here's the requested data visualization:"),
                    thread_id=thread_id,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    graph_data=parsed_response.get("graph_data"),
                    is_error=False
                )
        except (json.JSONDecodeError, TypeError):
            pass

        return AgentResponse(
            response=agent_response,
            thread_id=thread_id,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            graph_data=None,
            is_error=False
        )

    def _cleanup_stale_runs(self):
        """Clean up runs that have been active too long"""
        now = datetime.now()
        stale_threads = []
        
        for thread_id, start_time in self.active_runs.items():
            if now - start_time > timedelta(minutes=5):  # 5 minute timeout
                stale_threads.append(thread_id)
        
        for thread_id in stale_threads:
            try:
                print(f"Cleaning up stale run for thread {thread_id}")
                del self.active_runs[thread_id]
            except Exception as e:
                print(f"Error cleaning up stale run: {e}")

    @staticmethod
    def is_graph_prompt(prompt: str) -> bool:
        graph_keywords = ["generate graph", "show me a graph", "plot", "visualize", "graph", "chart", "trend"]
        prompt_lower = prompt.lower()
        return any(keyword in prompt_lower for keyword in graph_keywords)
    
    @staticmethod
    def is_pie_chart_prompt(prompt: str) -> bool:
        pie_keywords = ["pie chart", "distribution", "share", "percentage", "proportion"]
        prompt_lower = prompt.lower()
        return any(keyword in prompt_lower for keyword in pie_keywords)

    def delete_old_threads(self, keep_last_n: int = 3):
        """Clean up old threads while preserving active ones"""
        try:
            threads = list(self.agent_client.threads.list(order=ListSortOrder.DESCENDING))
            threads_to_delete = []
            
            for thread in threads[keep_last_n:]:
                # Don't delete threads with active runs
                if thread.id not in self.active_runs:
                    threads_to_delete.append(thread)
            
            for thread in threads_to_delete:
                print(f"Deleting thread: {thread.id}")
                self.agent_client.threads.delete(thread.id)

            print(f"Deleted {len(threads_to_delete)} old threads, kept {keep_last_n} latest.")
        except Exception as e:
            print(f"Error while deleting threads: {e}")