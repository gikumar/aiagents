# backend/app/agentfactory.py
from dataclasses import dataclass
import threading
import logging
import json
from datetime import datetime, timedelta
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
import ast
import json
import time
import zlib
import base64
from typing import Optional, Any, Dict
from app.utility.thread_cleanup_scheduler import register_agent_instance
from datetime import datetime, timedelta, timezone

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with higher level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

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
    STALE_RUN_THRESHOLD = timedelta(minutes=15)
    MAX_OUTPUT_SIZE = 900000  # 900KB to leave buffer room under 1MB limit
    MAX_RUN_WAIT_TIME = 30  # Maximum seconds to wait for a run to complete
    RUN_CHECK_INTERVAL = 1  # Seconds between run status checks
    
    def __init__(self):
        logger.info("🚀Initializing AgentFactory")
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
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(minutes=10)
        self.thread_lock = threading.Lock()
        register_agent_instance("OrchestratorAgent", self)
        logger.info("🚀AgentFactory initialized successfully")

    def mark_run_active(self, thread_id: str):
        logger.info(f"🚀Marking run {thread_id} as active")
        self.active_runs[thread_id] = datetime.now()

    def remove_run(self, thread_id: str):
        if thread_id in self.active_runs:
            logger.info(f"🚀Removing run {thread_id} from active runs")
            del self.active_runs[thread_id]

    def get_active_thread_ids(self):
        now = datetime.now()
        active_ids = [
            tid for tid, start_time in self.active_runs.items()
            if now - start_time < self.STALE_RUN_THRESHOLD
        ]
        logger.info(f"🚀Active thread IDs: {active_ids}")
        return active_ids

    def cleanup_stale_runs(self):
        now = datetime.now()
        stale = [tid for tid, t in self.active_runs.items() if now - t > self.STALE_RUN_THRESHOLD]
        if stale:
            logger.info(f"🚀Cleaning up stale runs: {stale}")
            for tid in stale:
                del self.active_runs[tid]

    def get_or_create_agent(self) -> str:
        logger.info("🚀Getting or creating agent")
        if self.agent is not None:
            logger.info("🚀Using existing agent instance")
            return self.agent.id

        registered_tools = [
            execute_databricks_query,
            get_insights_from_text,
            generate_graph_from_prompt
        ]
        logger.info(f"🚀Registered tools: {[t.__name__ for t in registered_tools]}")

        existing_agents = list(self.agent_client.list_agents())
        for agent in existing_agents:
            if agent.name == orchestrator_agent_name:
                logger.info(f"🚀Found existing agent: {agent.name} ({agent.id})")
                self.toolset = ToolSet()
                self.toolset.add(FunctionTool(registered_tools))
                self.agent_client.enable_auto_function_calls(self.toolset)
                self.agent = agent
                return self.agent.id

        logger.info(f"🚀Creating new agent: {orchestrator_agent_name}")
        self.toolset = ToolSet()
        self.toolset.add(FunctionTool(registered_tools))
        self.agent_client.enable_auto_function_calls(self.toolset)

        self.agent = self.agent_client.create_agent(
            model=MODEL_DEPLOYMENT_NAME,
            name=orchestrator_agent_name,
            instructions=orchestrator_instruction,
            toolset=self.toolset,
            top_p=0.89,
            temperature=0.01
        )
        logger.info(f"🚀Created new agent with ID: {self.agent.id}")
        return self.agent.id

    def _compress_data(self, data: Any) -> dict:
        """Compress data that exceeds size limits"""
        try:
            json_str = json.dumps(data)
            if len(json_str) <= self.MAX_OUTPUT_SIZE:
                return {"data": data, "compressed": False}
            
            compressed = zlib.compress(json_str.encode('utf-8'))
            encoded = base64.b64encode(compressed).decode('utf-8')
            return {
                "data": encoded,
                "compressed": True,
                "original_size": len(json_str),
                "compressed_size": len(encoded)
            }
        except Exception as e:
            logger.error(f"🚀Compression failed: {str(e)}")
            raise ValueError("Failed to compress data") from e

    def _decompress_data(self, compressed_data: dict) -> Any:
        """Decompress data that was previously compressed"""
        try:
            if not compressed_data.get("compressed", False):
                return compressed_data.get("data")
            
            decoded = base64.b64decode(compressed_data["data"].encode('utf-8'))
            decompressed = zlib.decompress(decoded)
            return json.loads(decompressed.decode('utf-8'))
        except Exception as e:
            logger.error(f"🚀Decompression failed: {str(e)}")
            raise ValueError("Failed to decompress data") from e

    def _wait_for_run_completion(self, thread_id: str, run_id: str) -> bool:
        """Wait for a run to complete or timeout"""
        start_time = time.time()
        while time.time() - start_time < self.MAX_RUN_WAIT_TIME:
            try:
                run = self.agent_client.runs.get(thread_id=thread_id, run_id=run_id)
                if run.status in ["completed", "failed", "cancelled", "expired"]:
                    return True
                time.sleep(self.RUN_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"🚀Error checking run status: {str(e)}")
                return False
        return False

    def process_request2(
        self,
        prompt: str,
        agent_mode: str = "Balanced",
        file_content: Optional[str] = None,
        chat_history: Optional[list] = None,
        thread_id: Optional[str] = None,
        max_retries: int = 3
    ) -> AgentResponse:
        logger.info(f"🚀Processing request with mode: {agent_mode}")
        try:
            if datetime.now() - self.last_cleanup > self.cleanup_interval:
                logger.info("🚀Running cleanup of stale runs")
                self.cleanup_stale_runs()
                self.last_cleanup = datetime.now()
            
            agent_id = self.get_or_create_agent()
            
            # Use thread lock to prevent concurrent modifications
            with self.thread_lock:
                thread = self._get_thread_with_retry(thread_id, max_retries)
                if isinstance(thread, AgentResponse):
                    logger.info("🚀Thread is busy with existing run")
                    return thread
                
                behavior_instruction = agent_behavior_instructions.get(agent_mode, "")
                full_instruction = f"""
                    [Orchestrator Instructions]
                    {orchestrator_instruction}

                    [Behavior Instructions - Mode: {agent_mode}]
                    {behavior_instruction}
                    """.strip()
                logger.info(f"🚀Using instructions:\n{full_instruction[:200]}...")

                if not thread_id:
                    logger.info("🚀Sending initial instruction message")
                    self._send_message_with_retry(
                        thread.id,
                        "assistant",
                        full_instruction,
                        max_retries
                    )

                user_message_content = prompt
                if file_content:
                    logger.info("🚀Appending file content to message")
                    user_message_content += f"\n\n[FILE_CONTENT_START]\n{file_content}\n[FILE_CONTENT_END]"

                logger.info("🚀Sending user message")
                self._send_message_with_retry(
                    thread.id,
                    "user",
                    user_message_content,
                    max_retries
                )

                self.mark_run_active(thread.id)
                logger.info("🚀Creating and processing run")
                run = self.agent_client.runs.create_and_process(
                    thread_id=thread.id,
                    agent_id=agent_id
                )

                logger.info("🚀Processing run results")
                return self._process_run_results(
                    run,
                    thread.id,
                    max_retries
                )

        except Exception as e:
            logger.error(f"🚀Error in process_request2: {str(e)}")
            logger.error(traceback.format_exc())
            error_msg = str(e)
            if "active run" in error_msg.lower():
                error_msg = "Please wait while I finish processing your previous request."
            elif "string_above_max_length" in error_msg:
                error_msg = "The response was too large. Please try a more specific query."
            return AgentResponse(
                response=f"An error occurred: {error_msg}",
                thread_id=thread_id if 'thread' in locals() else None,
                is_error=True
            )

    def _parse_output(self, output):
        if isinstance(output, dict):
            return output
        if isinstance(output, str):
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                try:
                    return ast.literal_eval(output)
                except Exception as e:
                    logger.info(f"🚀Failed to parse output string: {e}")
                    return output
        return output

    def _get_tool_output(self, run, tool_name: str) -> Optional[dict]:
        logger.info(f"🚀Getting tool output for: {tool_name}")
        logger.info(f"🚀_get_tool_output call run details: run_id={run.id}, thread_id={run.thread_id}")

        try:
            steps = list(self.agent_client.run_steps.list(
                run_id=run.id,
                thread_id=run.thread_id
            ))

            for step in steps:
                logger.info(f"🚀Inspecting step: run_id={getattr(step, 'run_id', None)}, thread_id={getattr(step, 'thread_id', None)}, kind={getattr(step, 'kind', None)}")

                if getattr(step, 'kind', '').lower() == "tool":
                    logger.info("🚀_get_tool_output: check step kind")
                    attrs = getattr(step, 'attributes', {})
                    if isinstance(attrs, dict):
                        logger.info("🚀_get_tool_output: graph data is of dict type")
                        func = attrs.get('function')
                        if func and func.get('name') == tool_name:
                            logger.info("🚀_get_tool_output: tool name matched for graph data")
                            output = func.get('output')
                            logger.info(f"🚀Found output in step.attributes.function: {output[:100] if isinstance(output, str) else output}")
                            return self._parse_output(output)

                if hasattr(step, 'tool_call'):
                    logger.info("🚀_get_tool_output: checking graph data in step.tool_call")
                    tc = step.tool_call
                    if getattr(tc, 'tool_name', None) == tool_name:
                        logger.info("🚀_get_tool_output: checking graph data in step.tool_call: tool name matched")
                        output = getattr(tc, 'output', None)
                        logger.info(f"🚀Found output in step.tool_call: {output[:100] if isinstance(output, str) else output}")
                        return self._parse_output(output)

                if hasattr(step, 'step_details') and hasattr(step.step_details, 'tool_calls'):
                    logger.info("🚀_get_tool_output: checking graph data in step.step_details.tool_calls")
                    for tool_call in step.step_details.tool_calls:
                        func = getattr(tool_call, 'function', None)
                        if func and func.get('name') == tool_name:
                            logger.info("🚀_get_tool_output: checking graph data in step.step_details.tool_calls: function name matched")
                            output = func.get('output')
                            logger.info(f"🚀Found output in step.step_details.tool_calls: {output[:100] if isinstance(output, str) else output}")
                            return self._parse_output(output)

        except Exception as e:
            logger.error(f"🚀Error getting tool output: {str(e)}")
            logger.error(traceback.format_exc())

        return None

    def _process_run_results(
        self,
        run,
        thread_id: str,
        max_retries: int
    ) -> AgentResponse:
        logger.info("🚀Processing run results")
        prompt_tokens = run.usage.prompt_tokens or 0
        completion_tokens = run.usage.completion_tokens or 0
        logger.info(f"🚀Token usage - Input: {prompt_tokens}, Output: {completion_tokens}")

        # Check for graph tool output first
        graph_output = self._get_tool_output(run, "generate_graph_from_prompt")
        
        if graph_output and graph_output.get("status") == "success":
            try:
                graph_data = graph_output.get("graph_data")
                if isinstance(graph_data, dict) and graph_data.get("compressed", False):
                    graph_data = self._decompress_data(graph_data)
                
                logger.info(f"🚀Graph data size: {len(json.dumps(graph_data)) if graph_data else 0} bytes")
                return AgentResponse(
                    response="Here's the requested graph:",
                    thread_id=thread_id,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    graph_data=graph_data,
                    response_type="graph"
                )
            except Exception as e:
                logger.error(f"🚀Failed to process graph output: {str(e)}")
                return AgentResponse(
                    response="Error processing graph data",
                    thread_id=thread_id,
                    is_error=True
                )

        # Get final agent message
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
                    logger.info(f"🚀Agent response: {content[:200]}...")
                    break
                    
        if agent_response is None:
            logger.info("🚀No direct agent response found")
            return AgentResponse(
                response="Agent did not provide a direct response",
                thread_id=thread_id,
                is_error=False,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens
            )

        if thread_id in self.active_runs:
            del self.active_runs[thread_id]

        logger.info("🚀Returning text response")
        return AgentResponse(
            response=agent_response,
            thread_id=thread_id,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            response_type="text",
            is_error=False
        )

    def _get_thread_with_retry(self, thread_id: Optional[str], max_retries: int):
        logger.info(f"🚀Getting thread with ID: {thread_id}")
        for attempt in range(max_retries):
            try:
                if thread_id:
                    # Check for any active runs
                    active_runs = list(self.agent_client.runs.list(
                        thread_id=thread_id,
                        status=["in_progress", "queued", "requires_action"]
                    ))
                    
                    if active_runs:
                        logger.info(f"🚀Active runs found: {[r.id for r in active_runs]}")
                        
                        # Wait for existing runs to complete
                        for run in active_runs:
                            if not self._wait_for_run_completion(thread_id, run.id):
                                if attempt == max_retries - 1:
                                    return AgentResponse(
                                        response="Please wait while I finish processing your previous request.",
                                        thread_id=thread_id,
                                        is_error=False
                                    )
                                continue
                    
                    # Additional check to ensure no pending messages
                    messages = list(self.agent_client.messages.list(thread_id=thread_id))
                    if messages and messages[-1].role == "user" and not messages[-1].completed:
                        if attempt == max_retries - 1:
                            return AgentResponse(
                                response="Your previous message is still being processed.",
                                thread_id=thread_id,
                                is_error=False
                            )
                        time.sleep(1 * (attempt + 1))
                        continue
                        
                    return self.agent_client.threads.get(thread_id)
                # elif self.current_thread:
                #     logger.info("🚀Using current thread")
                #     return self.current_thread
                elif self.current_thread:
                    # Check if we should start a new thread based on run count, token usage, or age
                    thread_info = self.agent_client.threads.get(self.current_thread.id)

                    runs = list(self.agent_client.runs.list(thread_id=self.current_thread.id))
                    
                    # Example: Count runs in this thread
                    run_count = len(runs)

                    # Example: Token usage check
                    total_tokens = sum(
                        (r.usage.prompt_tokens or 0) + (r.usage.completion_tokens or 0)
                        for r in runs
                    )

                    # Example: Age check
                    #thread_age = datetime.now() - thread_info.created_at
                    thread_age = datetime.now(timezone.utc) - thread_info.created_at

                    if run_count >= 20 or total_tokens > 45000 or thread_age > timedelta(hours=1):
                        logger.info("🚀Starting new thread due to limit reached")
                        thread = self.agent_client.threads.create()
                        self.current_thread = thread
                        return thread

                    logger.info("🚀Using existing thread")
                    return self.current_thread

                else:
                    logger.info("🚀Creating new thread")
                    thread = self.agent_client.threads.create()
                    self.current_thread = thread
                    return thread
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1 * (attempt + 1))


    def _send_message_with_retry(self, thread_id: str, role: str, content: str, max_retries: int):
        logger.info(f"🚀Sending {role} message to thread {thread_id}")
        for attempt in range(max_retries):
            try:
                self.agent_client.messages.create(
                    thread_id=thread_id,
                    role=role,
                    content=content
                )
                return
            except Exception as e:
                if "active run" in str(e):
                    if attempt < max_retries - 1:
                        # Wait for any active runs to complete
                        active_runs = list(self.agent_client.runs.list(
                            thread_id=thread_id,
                            status=["in_progress", "queued", "requires_action"]
                        ))
                        if active_runs:
                            self._wait_for_run_completion(thread_id, active_runs[0].id)
                        time.sleep(1 * (attempt + 1))
                        continue
                raise

    @staticmethod
    def is_graph_prompt(prompt: str) -> bool:
        graph_keywords = ["generate graph", "show me a graph", "plot", "visualize", "graph", "chart", "trend"]
        return any(k in prompt.lower() for k in graph_keywords)