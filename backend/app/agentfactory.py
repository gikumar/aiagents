#agentfactory.py
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet, ListSortOrder, MessageRole
from .config import PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME
from .config import orchestrator_agent_name, orchestrator_instruction, agent_behavior_instructions
from .tools import generate_graph_data, user_functions

import traceback
import json

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
        self.agent = None  # cache agent instance
        self.agent_client = AgentsClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            )
        )
        self.current_thread = None
        # self.toolset = ToolSet()
        # self.toolset.add(FunctionTool(user_functions))
        # self.agent_client.enable_auto_function_calls(self.toolset)


    #get or create the agent.
    def get_or_create_agent(self) -> str:
        """Deletes any previously created agent with the same name, then creates a new one."""

        """
        Returns the existing agent ID if available, otherwise creates one.
        Avoids deleting and recreating the agent on every call.
        """
        if self.agent is not None:
            return self.agent.id  # Already initialized

        # Check if agent with desired name already exists
        existing_agents = list(self.agent_client.list_agents())  
          
        for agent in existing_agents:
            if agent.name == orchestrator_agent_name:
                print(f"Reusing existing agent: {agent.name} ({agent.id})")
                
                # Set toolset again (required for auto function call)
                self.toolset = ToolSet()
                tool_functions = list(user_functions) + [generate_graph_data]
                self.toolset.add(FunctionTool(tool_functions))
                self.agent_client.enable_auto_function_calls(self.toolset)

                self.agent = agent
                return self.agent.id

        # No existing agent found — create a new one
        print(f"No existing agent found, creating a new one: {orchestrator_agent_name}")
    
        self.toolset = ToolSet()
        tool_functions = list(user_functions) + [generate_graph_data]
        self.toolset.add(FunctionTool(tool_functions))
        self.agent_client.enable_auto_function_calls(self.toolset)

        self.agent = self.agent_client.create_agent(
            model=MODEL_DEPLOYMENT_NAME,
            name=orchestrator_agent_name,
            instructions=orchestrator_instruction,
            toolset=self.toolset,
            top_p=0.01,
            temperature=0.99
        )

        print(f"New agent created: {self.agent.name} ({self.agent.id})")
        return self.agent.id
    

    def run_tool(self, tool_name: str, args: dict) -> str:
        """Dynamically runs the correct function tool from the toolset based on name."""
        for tool in self.toolset._tools:  # Accessing the actual FunctionTool instances
            if hasattr(tool, "functions"):
                for fn in tool.functions:
                    if fn.__name__ == tool_name:
                        return json.dumps(fn(**args))  # Ensure it returns a serializable string
                raise ValueError(f"No tool found for name: {tool_name}")
    
    
    def process_request2(
        self,
        prompt: str,
        agent_mode: str = "Balanced",
        file_content: Optional[str] = None,
        chat_history: Optional[list] = None,
        thread_id: Optional[str] = None,
    ) -> AgentResponse:
        try:
            agent_id = self.get_or_create_agent()

            # REUSE THREAD LOGIC
            if thread_id:
                thread = self.agent_client.threads.get(thread_id)
            elif self.current_thread:
                thread = self.current_thread
                print(f"Reusing thread ID: {thread.id}")
            else:
                thread = self.agent_client.threads.create()
                self.current_thread = thread
                print(f"Creating new thread ID: {thread.id}")

            behavior_instruction = agent_behavior_instructions.get(agent_mode, "")
            if not behavior_instruction:
                print(f"Warning: Unknown agent_mode '{agent_mode}', defaulting to basic instructions")

            full_instruction = f"""
                [Orchestrator Instructions]
                {orchestrator_instruction}

                [Behavior Instructions - Mode: {agent_mode}]
                {behavior_instruction}
                """.strip()

            if not thread_id:
                self.agent_client.messages.create(
                    thread_id=thread.id,
                    role="assistant",
                    content=full_instruction
                )

            # Prepare user message
            user_message_content = prompt
            if self.is_graph_prompt(prompt):
                user_message_content = "[Trigger generate_graph_data tool]\n" + user_message_content
            
            if file_content:
                user_message_content += f"\n\n[FILE_CONTENT_START]\n{file_content}\n[FILE_CONTENT_END]"

            if chat_history:
                for msg in chat_history:
                    role = msg["role"]
                    if role == "agent":
                        role = "assistant"
                    elif role not in {"user", "assistant"}:
                        print(f"Warning: Unsupported role '{role}', defaulting to 'user'")
                        role = "user"
                    self.agent_client.messages.create(
                        thread_id=thread.id,
                        role=role,
                        content=msg["content"]
                    )

            # Send the user's message
            self.agent_client.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_message_content
            )

            run = self.agent_client.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
            prompt_tokens = run.usage.prompt_tokens or 0
            completion_tokens = run.usage.completion_tokens or 0

            if run.status == "failed":
                print(f"Run failed: {run.last_error}")
                return AgentResponse(
                    response="An error occurred while processing the request.",
                    thread_id=thread.id,
                    is_error=True,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens
                )

            messages = list(self.agent_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING))
            agent_response = None

            for message in reversed(messages):
                if message.role == MessageRole.AGENT and message.text_messages:
                    agent_response = message.text_messages[-1].text.value
                    break

            # === Final response parsing ===
            if isinstance(agent_response, dict) and "graph_data" in agent_response:
                return AgentResponse(
                    response=agent_response.get("response", "Here's the requested data:"),
                    thread_id=thread.id,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    graph_data=agent_response.get("graph_data"),
                    is_error=False
                )

            try:
                parsed_response = json.loads(agent_response)
                if isinstance(parsed_response, dict) and "graph_data" in parsed_response:
                    return AgentResponse(
                        response=parsed_response.get("response", "Here's the requested data:"),
                        thread_id=thread.id,
                        input_tokens=prompt_tokens,
                        output_tokens=completion_tokens,
                        graph_data=parsed_response.get("graph_data"),
                        is_error=False
                    )
            except (json.JSONDecodeError, TypeError):
                pass

            return AgentResponse(
                response=agent_response,
                thread_id=thread.id,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                graph_data=None,
                is_error=False
            )

        except Exception as e:
            print("Exception in process_request2:")
            print(traceback.format_exc())
            return AgentResponse(
                response=f"An error occurred: {str(e)}",
                thread_id=thread.id if 'thread' in locals() else None,
                is_error=True
            )

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


    def delete_old_threads(self, keep_last_n: int = 10):
        """
        Deletes all threads except the most recent N threads.
        """
        try:
            threads = list(self.agent_client.threads.list(order=ListSortOrder.DESCENDING))
            print(f"Found {len(threads)} threads")

            # Keep the most recent N threads
            threads_to_delete = threads[keep_last_n:]

            for thread in threads_to_delete:
                print(f"Deleting thread: {thread.id}")
                self.agent_client.threads.delete(thread.id)

            print(f"Deleted {len(threads_to_delete)} old threads, kept {keep_last_n} latest.")
        except Exception as e:
            print(f"Error while deleting threads: {e}")
