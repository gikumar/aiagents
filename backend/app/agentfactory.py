# backend/app/agentfactory.py

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet, ListSortOrder, MessageRole
# Make sure to import all relevant config variables and tools
from .config import PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME, orchestrator_agent_name, orchestrator_instruction, agent_behavior_instructions
# NEW: Ensure all desired tools are imported here
from .tools import generate_graph_data, user_functions, execute_databricks_query, get_insights_from_text # <--- ADDED get_insights_from_text

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


    #get or create the agent.
    def get_or_create_agent(self) -> str:
        """
        Returns the existing agent ID if available, otherwise creates one.
        Avoids deleting and recreating the agent on every call.
        """
        if self.agent is not None:
            return self.agent.id  # Already initialized

        # Define the tools to be added.
        # These must be the actual function objects.
        # user_functions, if it contains callable functions, should be unpacked or iterated.
        # For simplicity, let's explicitly list the functions from tools.py that are actual tools.
        
        # Define a list of actual callable functions (tools)
        # Ensure generate_graph_data is not None if you intend to use it.
        # If user_functions contains actual callable functions, iterate its values.
        
        # Correctly assemble the list of tools to register
        # Only include functions that are actually meant to be called by the agent.
        # user_functions as an empty dict means it provides no tools directly.
        
        registered_tools = [
            execute_databricks_query,
            get_insights_from_text,
            # Conditionally add generate_graph_data if it's not None (meaning it was imported successfully)
            *([] if generate_graph_data is None else [generate_graph_data]),
            # If user_functions contains callable tools, add them like this:
            # *[f for f in user_functions.values() if callable(f)],
        ]

        # Check if agent with desired name already exists
        existing_agents = list(self.agent_client.list_agents())  
          
        for agent in existing_agents:
            if agent.name == orchestrator_agent_name:
                print(f"Reusing existing agent: {agent.name} ({agent.id})")
                
                # Set toolset again (required for auto function call)
                self.toolset = ToolSet()
                # NOW ADD THE ACTUAL FUNCTION OBJECTS
                self.toolset.add(FunctionTool(registered_tools)) # <--- CORRECTED LINE

                self.agent_client.enable_auto_function_calls(self.toolset)

                self.agent = agent
                return self.agent.id

        # No existing agent found — create a new one
        print(f"No existing agent found, creating a new one: {orchestrator_agent_name}")
    
        self.toolset = ToolSet()
        # NOW ADD THE ACTUAL FUNCTION OBJECTS
        self.toolset.add(FunctionTool(registered_tools)) # <--- CORRECTED LINE

        self.agent_client.enable_auto_function_calls(self.toolset)

        self.agent = self.agent_client.create_agent(
            model=MODEL_DEPLOYMENT_NAME,
            name=orchestrator_agent_name,
            instructions=orchestrator_instruction, # This now includes the detailed SQL generation guidance
            toolset=self.toolset,
            top_p=0.01, # Keep as is or adjust as needed
            temperature=0.99 # Keep as is or adjust as needed
        )

        print(f"New agent created: {self.agent.name} ({self.agent.id})")
        return self.agent.id
    

    def run_tool(self, tool_name: str, args: dict) -> str:
        """Dynamically runs the correct function tool from the toolset based on name."""
        # This method also needs to be updated to iterate over the 'registered_tools'
        # or have a direct mapping if that's preferred.
        # For simplicity, we can assume the toolset now correctly holds the FunctionTool instances.
        
        # This implementation iterates over the _tools, which are FunctionTool instances.
        # Each FunctionTool instance can contain multiple functions.
        # The agent client's auto-function-calls will map the tool_name to the actual function.
        # So, this 'run_tool' method is more for manual execution if needed.
        # It looks like your run_tool method is designed to iterate through the toolset
        # and find the function by name. This should work IF the FunctionTool was created correctly
        # with actual function objects.
        
        # Let's ensure the tool_name mapping works.
        # The agent client's auto-function-calls typically handle the direct mapping,
        # so this `run_tool` might not be strictly necessary if you're solely relying on `create_and_process`.
        # However, if it's being called, its logic should also reflect the correct tool objects.
        
        # The current run_tool method looks correct IF the FunctionTool was correctly populated with the functions.
        # Since we are fixing the FunctionTool creation, this should now function as expected.
        
        for tool in self.toolset._tools:  # Accessing the actual FunctionTool instances
            if hasattr(tool, "functions"): # Check if it's a FunctionTool instance
                for fn in tool.functions: # Iterate through the functions added to this FunctionTool
                    if fn.__name__ == tool_name:
                        return json.dumps(fn(**args))  # Call the found function
        raise ValueError(f"No tool found for name: {tool_name}") # If loop finishes, tool not found
    
    
    def process_request2(
        self,
        prompt: str,
        agent_mode: str = "Balanced",
        file_content: Optional[str] = None,
        chat_history: Optional[list] = None,
        thread_id: Optional[str] = None,
    ) -> AgentResponse:
        try:
            agent_id = self.get_or_create_agent() # This will now correctly register the tools

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

            # The full_instruction is crucial for guiding the agent.
            # It already incorporates the orchestrator_instruction from config.py
            # which now contains the SQL generation logic and schema.
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
                    role="assistant", # Setting the initial system-like instruction for the agent
                    content=full_instruction
                )

            # Prepare user message
            user_message_content = prompt
            
            if file_content:
                user_message_content += f"\n\n[FILE_CONTENT_START]\n{file_content}\n[FILE_CONTENT_END]"

            # Send the user's message
            self.agent_client.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_message_content
            )

            # The create_and_process method will handle the agent's multi-step tool calls
            run = self.agent_client.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
            prompt_tokens = run.usage.prompt_tokens or 0
            completion_tokens = run.usage.completion_tokens or 0

            if run.status == "failed":
                print(f"Run failed: {run.last_error}")
                return AgentResponse(
                    response=f"An error occurred while processing the request: {run.last_error.message if run.last_error else 'Unknown error'}",
                    thread_id=thread.id,
                    is_error=True,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens
                )

            messages = list(self.agent_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING))
            agent_response = None

            # Iterate messages in reverse to find the latest agent response
            for message in reversed(messages):
                if message.role == MessageRole.AGENT and message.text_messages:
                    agent_response = message.text_messages[-1].text.value
                    break
                elif message.role == MessageRole.TOOL and message.tool_code_messages:
                    # Continue searching for an AGENT role message
                    pass 
            
            if agent_response is None:
                return AgentResponse(
                    response="Agent did not provide a direct response. Check logs for tool outputs.",
                    thread_id=thread.id,
                    is_error=False,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens
                )

            # === Final response parsing ===
            try:
                parsed_response = json.loads(agent_response)
                if isinstance(parsed_response, dict) and "graph_data" in parsed_response:
                    return AgentResponse(
                        response=parsed_response.get("response", "Here's the requested data visualization:"),
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
                response=f"An internal server error occurred: {str(e)}",
                thread_id=thread_id if 'thread' in locals() else None,
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