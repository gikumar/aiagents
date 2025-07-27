from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet, ListSortOrder, MessageRole
from .tools import user_functions 
from .config import PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME
from .config import orchestrator_agent_name, orchestrator_instruction
@dataclass
class AgentResponse:
    response: str
    thread_id: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    graph_data: Optional[Dict[str, Any]] = None
    is_error: bool = False

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
        self.toolset = ToolSet()
        self.toolset.add(FunctionTool(user_functions))
        self.agent_client.enable_auto_function_calls(self.toolset)

    def get_or_create_agent(self) -> str:
        """Reuse the same agent if created; otherwise, create it."""
        if self.agent:
            return self.agent.id

        self.agent = self.agent_client.create_agent(
            model=MODEL_DEPLOYMENT_NAME,
            name= orchestrator_agent_name,
            instructions= orchestrator_instruction,
            toolset=self.toolset
        )
        print(f"Agent created: {self.agent.name} ({self.agent.id})")
        return self.agent.id

    def process_request2(
        self,
        prompt: str,
        agent_mode: str = "Balanced",
        file_content: Optional[str] = None,
        chat_history: Optional[list] = None,
        is_graph_request: bool = False,
        graph_type: str = "bar",
        thread_id: Optional[str] = None
    ) -> AgentResponse:
        try:
            agent_id = self.get_or_create_agent()
            thread = self.agent_client.threads.get(thread_id) if thread_id else self.agent_client.threads.create()
            print(f"Using thread ID: {thread.id}")

            message = self.agent_client.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
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
                    break  # only break after finding the first valid agent message

            if agent_response:
                return AgentResponse(
                    response=agent_response,
                    thread_id=thread.id,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens
                )
            else:
                return AgentResponse(
                    response="No agent response was returned.",
                    thread_id=thread.id,
                    is_error=True,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens
                )

        except Exception as e:
            print("Exception in process_request2:")
            print(traceback.format_exc())
            return AgentResponse(
                response="An internal error occurred.",
                thread_id=None,
                is_error=True
            )
