#Sharing 1st file just keep it and do not analyze until i confirm I have shared all the files
#/backedn/app/agentfactory.py
import json
import threading
import traceback
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
from .tools import generate_graph_data, user_functions
from .agsqlquerygenerator import AGSQLQueryGenerator

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
            "status": "error" if self.is_error else "success",
        }


class AgentFactory:
    _lock = threading.Lock()

    def __init__(self):
        print("Initializing AgentFactory")
        self.agent = None
        self.current_thread = None
        self.agent_client = AgentsClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True,
            ),
        )

    def get_or_create_agent(self) -> str:
        print("Fetching or creating orchestrator agent")
        if self.agent is not None:
            print(f"Using cached agent: {self.agent.name} ({self.agent.id})")
            return self.agent.id

        with AgentFactory._lock:
            if self.agent is not None:
                print(f"Using cached agent after acquiring lock: {self.agent.name} ({self.agent.id})")
                return self.agent.id

            existing_agents = list(self.agent_client.list_agents())
            print(f"Found {len(existing_agents)} existing agents")

            for agent in existing_agents:
                if agent.name == orchestrator_agent_name:
                    print(f"Reusing existing agent: {agent.name} ({agent.id})")
                    self._setup_tools()
                    self.agent = agent
                    return self.agent.id

            print(f"Creating new agent: {orchestrator_agent_name}")
            self._setup_tools()
            self.agent = self.agent_client.create_agent(
                model=MODEL_DEPLOYMENT_NAME,
                name=orchestrator_agent_name,
                instructions=orchestrator_instruction,
                toolset=self.toolset,
                top_p=0.01,
                temperature=0.5,
            )
            print(f"New agent created: {self.agent.name} ({self.agent.id})")
            return self.agent.id

    def _setup_tools(self):
        tool_functions = list(user_functions) + [generate_graph_data]
        self.toolset = ToolSet()
        self.toolset.add(FunctionTool(tool_functions))
        self.agent_client.enable_auto_function_calls(self.toolset)
        print(f"Toolset with {len(tool_functions)} tools enabled")

    def run_tool(self, tool_name: str, args: dict) -> str:
        print(f"Running tool: {tool_name} with args: {args}")
        for tool in self.toolset._tools:
            if hasattr(tool, "functions"):
                for fn in tool.functions:
                    if fn.__name__ == tool_name:
                        result = fn(**args)
                        print(f"Tool {tool_name} result: {result}")
                        return json.dumps(result)
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
            print(f"Processing request with prompt: {prompt}")
            agent_id = self.get_or_create_agent()

            if thread_id:
                thread = self.agent_client.threads.get(thread_id)
                print(f"Using provided thread ID: {thread.id}")
            elif self.current_thread:
                thread = self.current_thread
                print(f"Reusing current thread ID: {thread.id}")
            else:
                thread = self.agent_client.threads.create()
                self.current_thread = thread
                print(f"Created new thread ID: {thread.id}")

            behavior_instruction = agent_behavior_instructions.get(agent_mode, "")
            if not behavior_instruction:
                print(f"Warning: Unknown agent_mode '{agent_mode}'")

            full_instruction = f"""
                [Orchestrator Instructions]
                {orchestrator_instruction}

                [Behavior Instructions - Mode: {agent_mode}]
                {behavior_instruction}
                """.strip()

            if not thread_id:
                print("Injecting system instruction message to thread")
                self.agent_client.messages.create(
                    thread_id=thread.id, role="assistant", content=full_instruction
                )

            user_message_content = prompt
            if self.is_graph_prompt(prompt):
                user_message_content = "[Trigger generate_graph_data tool]\n" + user_message_content

            if file_content:
                user_message_content += f"\n\n[FILE_CONTENT_START]\n{file_content}\n[FILE_CONTENT_END]"

            print(f"Sending user message: {user_message_content}")
            self.agent_client.messages.create(
                thread_id=thread.id, role="user", content=user_message_content
            )

            run = self.agent_client.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
            print(f"Run created with status: {run.status}")
            prompt_tokens = run.usage.prompt_tokens or 0
            completion_tokens = run.usage.completion_tokens or 0

            if run.status == "failed":
                print(f"Run failed: {run.last_error}")
                return AgentResponse(
                    response="An error occurred while processing the request.",
                    thread_id=thread.id,
                    is_error=True,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                )

            messages = list(self.agent_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING))
            print(f"Retrieved {len(messages)} messages from thread")
            agent_response = None

            for message in reversed(messages):
                if message.role == MessageRole.AGENT and message.text_messages:
                    agent_response = message.text_messages[-1].text.value
                    break

            print(f"Agent raw response: {agent_response}")

            try:
                parsed_response = json.loads(agent_response)
                if isinstance(parsed_response, dict) and "graph_data" in parsed_response:
                    return AgentResponse(
                        response=parsed_response.get("response", "Here's the requested data:"),
                        thread_id=thread.id,
                        input_tokens=prompt_tokens,
                        output_tokens=completion_tokens,
                        graph_data=parsed_response.get("graph_data"),
                        is_error=False,
                    )
            except (json.JSONDecodeError, TypeError):
                print("Response not JSON parseable or not a graph result")

            return AgentResponse(
                response=agent_response,
                thread_id=thread.id,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                graph_data=None,
                is_error=False,
            )

        except Exception as e:
            print("Exception in process_request2:")
            print(traceback.format_exc())
            return AgentResponse(
                response=f"An error occurred: {str(e)}",
                thread_id=thread.id if 'thread' in locals() else None,
                is_error=True,
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
        try:
            threads = list(self.agent_client.threads.list(order=ListSortOrder.DESCENDING))
            print(f"Found {len(threads)} threads")
            threads_to_delete = threads[keep_last_n:]

            for thread in threads_to_delete:
                print(f"Deleting thread: {thread.id}")
                self.agent_client.threads.delete(thread.id)

            print(f"Deleted {len(threads_to_delete)} old threads, kept {keep_last_n} latest")
        except Exception as e:
            print(f"Error while deleting threads: {e}")