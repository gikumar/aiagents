# agentfactory.py
import uuid
import traceback
import pandas as pd
import os
import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionTool

from .tools import fetch_weather
#from .tools import get_or_create_agent, planner_strategy
from .config import agent_behavior_instructions, PROJECT_ENDPOINT, DATABRICKS_HTTP_PATH, MODEL_DEPLOYMENT_NAME

from typing import Any, Callable, Set, Dict, List, Optional

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
        # Initialize token counts
        prompt_tokens = 0
        completion_tokens = 0
        tool_outputs_for_submission = []

        try:
            # Initialize the AI project
            project_client = AIProjectClient(
                credential=DefaultAzureCredential(),
                endpoint=PROJECT_ENDPOINT
            )

            user_functions = {fetch_weather}
            functions = FunctionTool(functions=user_functions)


            with project_client:
                agent = project_client.agents.create_agent(
                    model= MODEL_DEPLOYMENT_NAME,
                    name="weather-agent",
                    instructions="You are a helpful agent. When needed, use fetch_weather.",
                    tools=functions.definitions
                )

                print(f"Agent created, ID = {agent.id}")

                style_instructions = {
                    "Short Answer": "Give a very brief and to-the-point answer.",
                    "Balanced": "Answer clearly and concisely with key insights.",
                    "Detailed": "Provide a comprehensive and detailed analysis with all supporting reasoning.",
                    "Structured": "Provide your answer in a highly structured format, using markdown headings, bullet points, and numbered lists where appropriate to organize information clearly."
                }

                thread = project_client.agents.threads.create()
                project_client.agents.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content="Tell me the weather in London."
                )

                run = project_client.agents.runs.create(thread_id=thread.id, agent_id=agent.id)

                # 3. Poll run status, handle function call
                while run.status in ["queued", "in_progress", "requires_action"]:
                    time.sleep(1)
                    
                    run = project_client.agents.runs.get(thread_id=thread.id, run_id=run.id)
                    
                    if run.status == "failed":
                        return AgentResponse(
                            response=f"Run failed: {run.last_error}",
                            thread_id=thread.id,
                            is_error=True,
                            input_tokens=0, # Ensure integer value
                            output_tokens=0  # Ensure integer value
                        )
                    if run.status == "requires_action":
                        calls = run.required_action.submit_tool_outputs.tool_calls
                        outputs = []
                        for call in calls:
                            if call.function.name == "fetch_weather":
                                result = fetch_weather("London")
                                outputs.append({"tool_call_id": call.id, "output": result})
                        
                        project_client.agents.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=outputs)

                        print("Final status:", run.status)

                messages = project_client.agents.messages.list(thread_id=thread.id)
                # for msg in messages:
                #     print(f"{msg['role']}: {msg['content']}")

                for msg in reversed(list(messages)):
                    if msg.role == "assistant" and msg.text_messages:
                        response_text = msg.text_messages[-1].text.value
                        break # Found the latest assistant message, break the loop
                
                return AgentResponse(
                    response=response_text,
                    thread_id=thread.id,
                    input_tokens=111, # Use actual token counts
                    output_tokens=222 # Use actual token counts
                    )
        except Exception as e:
            # Log the full error for debugging
            print(f"Error processing request: {e}\n{traceback.format_exc()}")
            return AgentResponse(
                response=f"An unexpected error occurred. Please check the server logs for details.",
                thread_id=123,
                is_error=True,
                input_tokens=0, # Ensure integer value
                output_tokens=0  # Ensure integer value
            )


    