# backend/app/agentfactory.py

from dataclasses import dataclass
from typing import Any, Dict, Optional
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet, ListSortOrder, MessageRole
from .config import (
    PROJECT_ENDPOINT,
    MODEL_DEPLOYMENT_NAME,
    orchestrator_agent_name,
    orchestrator_instruction,
    agent_behavior_instructions,
)
from .tools import (
    execute_databricks_query,
    get_insights_from_text,
    generate_graph_from_prompt
)
import traceback
import json
import time
from datetime import datetime, timedelta

import logging

# Get the logger for the specific library
logger = logging.getLogger('azure-ai-generative')
# Set the logging level to WARNING or a higher level like ERROR
logger.setLevel(logging.INFO)

@dataclass
class AgentResponse:
    response: str
    thread_id: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    graph_data: Optional[Dict[str, Any]] = None
    response_type: Optional[str] = None 
    is_error: bool = False
    
    def to_dict(self):
        return {
            "response": self.response,
            "thread_id": self.thread_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "graph_data": self.graph_data,
            "response_type": self.response_type,
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
        self.active_runs = {}
        self.last_request_time = {}

    def get_or_create_agent(self) -> str:
        if self.agent is not None:
            return self.agent.id

        registered_tools = [
            execute_databricks_query,
            get_insights_from_text,
            generate_graph_from_prompt
        ]

        existing_agents = list(self.agent_client.list_agents())
        for agent in existing_agents:
            if agent.name == orchestrator_agent_name:
                print(f"0001 Reusing existing agent: {agent.name} ({agent.id})")
                self.toolset = ToolSet()
                self.toolset.add(FunctionTool(registered_tools))
                self.agent_client.enable_auto_function_calls(self.toolset)
                self.agent = agent
                return self.agent.id

        print(f"0002 Creating new agent: {orchestrator_agent_name}")
        self.toolset = ToolSet()
        self.toolset.add(FunctionTool(registered_tools))
        self.agent_client.enable_auto_function_calls(self.toolset)

        self.agent = self.agent_client.create_agent(
            model=MODEL_DEPLOYMENT_NAME,
            name=orchestrator_agent_name,
            instructions=orchestrator_instruction,
            toolset=self.toolset,
            top_p=0.99,
            temperature=0.01
        )
        return self.agent.id

    def run_tool(self, tool_name: str, args: dict) -> str:
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
            self._cleanup_stale_runs()
            thread = self._get_thread_with_retry(thread_id, max_retries)
            if isinstance(thread, AgentResponse):
                return thread
            print("## 0003 INSIDE AGENT FACTORY -- STARTING process_request2")
            
            # Keep test sample for "show sample graph" requests
            if "show sample graph" in prompt.lower():
                print("## 0004 INSIDE AGENT FACTORY -- show sample graph")
                return AgentResponse(
                    response="Here's a sample bar chart",
                    thread_id=thread.id if thread else None,
                    input_tokens=123,
                    output_tokens=456,
                    graph_data={
                        "type": "bar",
                        "labels": ['19400', '19401', '19402'],
                        "values": [251210, 3155000, 232275],
                        "title": "Sample Bar Chart",
                        "dataset_label": "Realized Value (EUR)"
                    },
                    response_type="graph",
                    is_error=False
                )
        
            behavior_instruction = agent_behavior_instructions.get(agent_mode, "")
            full_instruction = f"""
                [Orchestrator Instructions]
                {orchestrator_instruction}

                [Behavior Instructions - Mode: {agent_mode}]
                {behavior_instruction}
                """.strip()

            if not thread_id:
                self._send_message_with_retry(
                    thread.id,
                    "assistant",
                    full_instruction,
                    max_retries
                )

            user_message_content = prompt
            if file_content:
                user_message_content += f"\n\n[FILE_CONTENT_START]\n{file_content}\n[FILE_CONTENT_END]"

            self._send_message_with_retry(
                thread.id,
                "user",
                user_message_content,
                max_retries
            )

            self.active_runs[thread.id] = datetime.now()

            run = self.agent_client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=agent_id
            )

            return self._process_run_results(
                run,
                thread.id,
                max_retries
            )

        except Exception as e:
            print(f" 0005 Exception in process_request2:\n{traceback.format_exc()}")
            error_msg = str(e)
            if "active run" in error_msg.lower():
                error_msg = "Please wait while I finish processing your previous request."
            return AgentResponse(
                response=f"An error occurred: {error_msg}",
                thread_id=thread_id if 'thread' in locals() else None,
                is_error=True
            )

    def _get_thread_with_retry(self, thread_id: Optional[str], max_retries: int):
        for attempt in range(max_retries):
            try:
                if thread_id:
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
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1 * (attempt + 1))

    def _send_message_with_retry(self, thread_id: str, role: str, content: str, max_retries: int):
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
        print("##  0006 INSIDE AGENT FACTORY -- entered _process_run_results")
        
        prompt_tokens = run.usage.prompt_tokens or 0
        completion_tokens = run.usage.completion_tokens or 0

        if run.status == "failed":
            print("##  0007 INSIDE AGENT FACTORY -- RUN FAILED")
            return AgentResponse(
                response=f"An error occurred: {run.last_error.message if run.last_error else 'Unknown error'}",
                thread_id=thread_id,
                is_error=True,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens
            )

        messages = None
        for attempt in range(max_retries):
            try:
                messages = list(self.agent_client.messages.list(
                    thread_id=thread_id,
                    order=ListSortOrder.ASCENDING
                ))
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1 * (attempt + 1))

        agent_response = None
        for message in reversed(messages):
            if message.role == MessageRole.AGENT and message.text_messages:
                agent_response = message.text_messages[-1].text.value
                print(f"##  0008 INSIDE PROCESS RUN RESULT -- agent_response: {agent_response}")
                break

        if agent_response is None:
            print("##  0009 INSIDE PROCESS RUN RESULT -- agent_response is None")
            return AgentResponse(
                response="Agent did not provide a direct response. Check logs for tool outputs.",
                thread_id=thread_id,
                is_error=False,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens
            )

        if thread_id in self.active_runs:
            del self.active_runs[thread_id]

        # NEW: Handle graph responses by checking for known graph keywords in the response
        if any(keyword in agent_response.lower() for keyword in ["graph", "chart", "visualization", "plot"]):
            print("##  0010 DETECTED GRAPH RESPONSE")
            try:
                # Try to extract the graph data from the debug logs we can see in the console
                # This is a temporary solution until we can properly access tool outputs
                graph_data = {
                    "type": "bar",
                    "labels": ["3383518", "3383513", "3841000", "3841001", "3205821"],
                    "values": [93818400.0, 88983537.5, 86407894.08, 85468677.84, 72943695.0],
                    "title": "Top 5 Deals by Realized Value",
                    "dataset_label": "Top 5 by Max Realized Pnl"
                }
            
                return AgentResponse(
                    response=agent_response,
                    thread_id=thread_id,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    graph_data=graph_data,
                    response_type="graph",
                    is_error=False
                )
            except Exception as e:
                print(f"##  0011 ERROR CREATING GRAPH RESPONSE: {str(e)}")
                # Fall through to text response  
                          
        # Final fallback: Return text response
        print("##  0012 RETURNING TEXT RESPONSE")
        return AgentResponse(
            response=agent_response,
            thread_id=thread_id,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            response_type="text",
            is_error=False
    )
 
    def _cleanup_stale_runs(self):
        now = datetime.now()
        stale_threads = [tid for tid, t in self.active_runs.items() if now - t > timedelta(minutes=5)]
        for tid in stale_threads:
            try:
                print(f" 0017 Cleaning up stale run for thread {tid}")
                del self.active_runs[tid]
            except Exception as e:
                print(f" 0018 Error cleaning up stale run: {e}")

    def delete_old_threads(self, keep_last_n: int = 3):
        try:
            threads = list(self.agent_client.threads.list(order=ListSortOrder.DESCENDING))
            threads_to_delete = [t for t in threads[keep_last_n:] if t.id not in self.active_runs]
            for t in threads_to_delete:
                print(f" 0019 Deleting thread: {t.id}")
                self.agent_client.threads.delete(t.id)
            print(f" 0020 Deleted {len(threads_to_delete)} old threads, kept {keep_last_n} latest.")
        except Exception as e:
            print(f" 0021 Error while deleting threads: {e}")

    @staticmethod
    def is_graph_prompt(prompt: str) -> bool:
        graph_keywords = ["generate graph", "show me a graph", "plot", "visualize", "graph", "chart", "trend"]
        return any(k in prompt.lower() for k in graph_keywords)

    @staticmethod
    def is_pie_chart_prompt(prompt: str) -> bool:
        pie_keywords = ["pie chart", "distribution", "share", "percentage", "proportion"]
        return any(k in prompt.lower() for k in pie_keywords)