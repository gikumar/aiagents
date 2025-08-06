# backend/app/agentfactory.py

from dataclasses import dataclass
import re
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
from .tools import generate_graph_data_from_results 


# Get the logger for the specific library
logger = logging.getLogger('azure-ai-generative')
# Set the logging level to WARNING or a higher level like ERROR
logger.setLevel(logging.ERROR)

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
        print("0001A inside get_or_create_agent")
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
            print("inside run_tool for loop")
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
            
            print("## 0003 STARTING process_request2")
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

            # Get tool outputs for graph generation
            #graph_data = self._get_tool_output(run, "generate_graph_from_prompt")
            graph_data = generate_graph_from_prompt(prompt)
            
            
            print("graph data in agent fatcory after calling get_tool_output")
            print(graph_data)


            return self._process_run_results(
                run,
                thread.id,
                max_retries,
                graph_data  # Pass graph data to results processor
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
        


    def _get_tool_output(self, run, tool_name: str) -> Optional[Dict]:
        """Extracts output from a specific tool call in the run"""
        try:
            print("extracting the tool output for = ", tool_name)
            steps = list(self.agent_client.run_steps.list(
                run_id=run.id,
                thread_id=run.thread_id
            ))
            
            for step in steps:
                if step.type == "tool":
                    print("for tool name: ", tool_name)
                    if hasattr(step, 'tool_call') and step.tool_call.tool_name == tool_name:
                        output = step.tool_call.output
                        if isinstance(output, str):
                            return json.loads(output)
                        return output
                    elif hasattr(step, 'step_details') and hasattr(step.step_details, 'tool_calls'):
                        for tool_call in step.step_details.tool_calls:
                            if tool_call.function.name == tool_name:
                                output = tool_call.function.output
                                if isinstance(output, str):
                                    return json.loads(output)
                                return output
        except Exception as e:
            print(f"Error getting tool output: {str(e)}")
            traceback.print_exc()
        return None
    
        
    def _process_tool_outputs_for_graph(self, run, prompt: str) -> Optional[Dict]:
        """Extracts and processes tool outputs for graph generation"""
        graph_data = None
        try:
            # Get all steps in the run
            steps = list(run.steps)
            
            # Find the last tool call that generated graph data
            for step in reversed(steps):
                if step.type == "tool" and step.tool_name == "generate_graph_from_prompt":
                    try:
                        # Parse tool output
                        tool_output = json.loads(step.output)
                        
                        # Extract graph data if available
                        if tool_output.get("status") == "success" and tool_output.get("graph_data"):
                            graph_data = tool_output["graph_data"]
                            break
                            
                    except json.JSONDecodeError:
                        print(f"Error parsing tool output: {step.output}")
                        continue
                        
        except Exception as e:
            print(f"Error processing tool outputs: {str(e)}")
            
        return graph_data


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


    def _process_run_results(
            self,
            run,
            thread_id,
            max_retries,
            graph_data: Optional[Dict] = None
        ) -> AgentResponse:
        print("##  calling _process_run_results after graph data is generated")
    
        prompt_tokens = run.usage.prompt_tokens or 0
        completion_tokens = run.usage.completion_tokens or 0

        if run.status == "failed":
            print("##  run had a failed status ##")
            return AgentResponse(
                response=f"An error occurred: {run.last_error.message if run.last_error else 'Unknown error'}",
                thread_id=thread_id,
                is_error=True,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens
            )
            
        if graph_data is None:
            print("graph data received as None in process_run_results")
            try:
                print("# Method 1 to generate graph data: Try to get graph data from run steps")
                try:
                    steps = list(self.agent_client.run_steps.list(
                        run_id=run.id,
                        thread_id=run.thread_id
                    ))
                
                    for step in steps:
                        if step.type == "tool":
                            if hasattr(step, 'tool_call') and step.tool_call.tool_name == "generate_graph_from_prompt":
                                print("## has step as tool_call -- generating the graph data form generate_graph_from_prompt tool run")
                                graph_data = json.loads(step.tool_call.output)
                                print("## Found graph data in generate_graph_from_prompt tool call")
                                print("graph_data")
                                print(graph_data)
                                break
                            elif hasattr(step, 'step_details') and hasattr(step.step_details, 'tool_calls'):
                                print("## has step as step_details -- generating the graph data form generate_graph_from_prompt tool run")
                                for tool_call in step.step_details.tool_calls:
                                    if tool_call.function.name == "generate_graph_from_prompt":
                                        print("## found in step_details for generate_graph_from_prompt tool run")
                                        graph_data = json.loads(tool_call.function.output)
                                        print("graph_data")
                                        print(graph_data)
                                        break
                except Exception as e:
                    print(f"Error extracting graph data from run steps: {str(e)}")
                    traceback.print_exc()

                
                print("# Method 2: Try to parse from message content if tools failed")
                messages = list(self.agent_client.messages.list(
                    thread_id=thread_id,
                    order=ListSortOrder.ASCENDING
                ))
            
                for message in reversed(messages):
                    if message.role == MessageRole.AGENT and message.text_messages:
                        agent_response = message.text_messages[-1].text.value
                        print("check if data is as follow found in agent response")
                        if "data is as follows" in agent_response:
                            print("yes- data is as follow found in agent response, now extract it..")
                            graph_data = self._extract_data_from_response(agent_response)
                            print("extracted graph data")
                            print(graph_data)
                            if graph_data:
                                print("## Extracted graph data is not blank")
                                break
            except Exception as e:
                print(f"Error processing graph data in process run results: {str(e)}")
                traceback.print_exc()

        print("# Preapring the agent FINAL response")
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
                content = message.text_messages[-1].text.value
                if "[Orchestrator Instructions]" not in content:
                    agent_response = content
                    print(f"##  AGENT FINAL RESPONSE MESSAGE -- agent_response: {agent_response}")
                    break
                    
        if agent_response is None:
            print("##  AGENT FINAL RESPONSE MESSAGE is None")
            return AgentResponse(
                response="Agent did not provide a direct response. Check logs for tool outputs.",
                thread_id=thread_id,
                is_error=False,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens
            )

        if thread_id in self.active_runs:
            del self.active_runs[thread_id]

        print("# Preapring final agent response with graph data if available")
        if graph_data and (graph_data.get("status") == "success" or "labels" in graph_data):
            print("##  Preapring final agent response --graph data is availble with status success or has labels")
            print("## Preapring final agent response --retriving graph data in any naming convention")
            final_graph_data = graph_data.get("graphData") or graph_data.get("graph_data") or graph_data
            
            print("### PRINTING FINAL GRAPH DATA #####")
            print(final_graph_data)

            print("# NOW CHECKING graph data HAS required ATTRIBUTES AVAILABLE")
            if not all(key in final_graph_data for key in ["labels", "values"]):
                print("## FINAL Graph data IS missing required fields, falling back to text")
                return AgentResponse(
                    response=agent_response,
                    thread_id=thread_id,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    response_type="text",
                    is_error=False
                )
            return AgentResponse(
                response=agent_response,
                thread_id=thread_id,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                graph_data=final_graph_data,
                response_type="graph",
                is_error=False
            )
                            
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
    
    def _extract_data_from_response(self, response_text: str) -> Optional[Dict]:
        """Extract graph data directly from response text when tools fail"""
        try:
            print("# Example pattern matching for data format")
            deal_nums_match = re.search(r"Deal Numbers:\s*(\[[^\]]+\])", response_text)
            pnl_values_match = re.search(r"Realized PnL Values:\s*(\[[^\]]+\])", response_text)
            
            if deal_nums_match and pnl_values_match:
                labels = json.loads(deal_nums_match.group(1))
                values = json.loads(pnl_values_match.group(1))
                values = [v/1e9 for v in values]  # Convert to billions
                
                return {
                    "type": "bar",
                    "labels": labels,
                    "values": values,
                    "dataset_label": "Realized PnL (in billions)",
                    "title": "Top Deals by Realized PnL"
                }
        except Exception as e:
            print(f"Error extracting data from response: {str(e)}")
        return None

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