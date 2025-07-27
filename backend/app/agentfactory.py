# agentfactory.py
import uuid
import traceback
import pandas as pd
import os
import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

#from azure.ai.projects import AIProjectClient
#from azure.ai.projects.models import ToolSet

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet, ListSortOrder, MessageRole
#from user_functions import user_functions

from .config import agent_behavior_instructions, PROJECT_ENDPOINT, DATABRICKS_HTTP_PATH, MODEL_DEPLOYMENT_NAME
from .config import query, graphquery
from .config import orchestrator_agent_name, orchestrator_instruction
from typing import Any, Callable, Set, Dict, List, Optional
from .tools import user_functions 
#from tools import user_functions
#from .tools import register_tools
#from .tools import fetch_weather, get_deals_data


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
        self.threads = {}
        self.agent_modes = {
            "Balanced": {"max_tokens": 5000, "temperature": 0.7},
            "Short": {"max_tokens": 1000, "temperature": 0.5},
            "Detailed": {"max_tokens": 3000, "temperature": 0.8},
            "Structured": {"max_tokens": 4000, "temperature": 0.6}
        }

    #called from main.py ask_agent method- agent based implementaion   
    def process_request2(self,
                       prompt: str,
                       agent_mode: str = "Balanced",
                       file_content: Optional[str] = None,
                       chat_history: Optional[list] = None,
                       is_graph_request: bool = False,
                       graph_type: str = "bar") -> AgentResponse:
        """
        Process user request and generate appropriate response
        """       
        try:
            prompt_tokens = 0
            completion_tokens = 0

            # Connect to the Agent client
            agent_client = AgentsClient(
                endpoint=PROJECT_ENDPOINT,
                credential=DefaultAzureCredential
                (exclude_environment_credential=True,
                exclude_managed_identity_credential=True)
                )

            with agent_client:
                functions = FunctionTool(user_functions)
                toolset = ToolSet()
                toolset.add(functions)
                agent_client.enable_auto_function_calls(toolset)

                agent = agent_client.create_agent(
                    model=MODEL_DEPLOYMENT_NAME,
                    name="support-agent",
                    instructions="""You are a technical support agent.
                                    When a user has a technical issue, you get their email address and a description of the issue.
                                    Then you use those values to submit a support ticket using the function available to you.
                                    If a file is saved, tell the user the file name.
                                """,
                    toolset=toolset
                )

                thread = agent_client.threads.create()
                print(f"You're chatting with: {agent.name} ({agent.id})")    

                # Loop until the user types 'quit'
                while True:
                    user_prompt = prompt
                    # Send a prompt to the agent
                    message = agent_client.messages.create(
                        thread_id=thread.id,
                        role="user",
                        content=user_prompt
                        )
                    
                    run = agent_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
                    prompt_tokens = run.usage.prompt_tokens if run.usage.prompt_tokens is not None else 0
                    completion_tokens = run.usage.completion_tokens if run.usage.completion_tokens is not None else 0
                    
                    # Check the run status for failures            
                    if run.status == "failed":                
                        print(f"Run failed: {run.last_error}")
                        return AgentResponse(
                            response=f"An unexpected error occurred. Please check the server logs for details.",
                            thread_id=thread.id,
                            is_error=True,
                            input_tokens=prompt_tokens, # Ensure integer value
                            output_tokens=completion_tokens  # Ensure integer value
            )
                    
                    # Get the conversation history        
                    print("\nConversation Log:\n")        
                    #messages = agent_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)        
                    messages = list(agent_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING))

                    agent_response = None

                    for message in reversed(messages):  # loop from latest to oldest
                        if message.role == MessageRole.AGENT and message.text_messages:
                            agent_response = message.text_messages[-1].text.value
                        break
                                        
                    if agent_response:
                        print(f"Agent: {agent_response}\n")
                        return AgentResponse(
                            response=agent_response,
                            thread_id=thread.id,
                            is_error=False,
                            input_tokens=prompt_tokens,
                            output_tokens=completion_tokens
                        )
                    else:
                        print("No agent response found.")
                        return AgentResponse(
                            response="No agent response found.",
                            thread_id=thread.id,
                            is_error=True,
                            input_tokens=prompt_tokens,
                            output_tokens=completion_tokens
                        )
        finally:
                "closed"

                


    