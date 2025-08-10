#Do not begin processing or making changes until I have shared all the files and explicitly confirm that I am done.
# backend/app/agsqlquerygenerator.py

import threading
import logging
from datetime import datetime, timedelta
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ListSortOrder, MessageRole

from app.utility.agent_registry import register_agent_instance

from .configagsqlquerygenerator import (
    PROJECT_ENDPOINT,
    MODEL_DEPLOYMENT_NAME,
    sql_query_generator_agent_name,
    sql_query_generator_instruction
)
from .sql_query_generator_instruction import build_sql_instruction

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.NullHandler())

class AGSQLQueryGenerator:
    _lock = threading.Lock()

    def __init__(self):
        logger.info("Initializing AGSQLQueryGenerator...")
        self.agent = None
        self.agent_client = AgentsClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            )
        )
        logger.info("AgentsClient initialized successfully")

        self.active_runs = {}
        self.run_timestamps = {}
        self.cleanup_interval = timedelta(minutes=5)
        self.last_cleanup = datetime.min

        register_agent_instance("SQLQueryGeneratorAgent", self)

        logger.info("AgentsClient initialized successfully")

    def get_or_create_sql_agent(self):
        if self.agent is not None:
            return self.agent

        with AGSQLQueryGenerator._lock:
            if self.agent is not None:
                return self.agent

            for agent in self.agent_client.list_agents():
                if agent.name == sql_query_generator_agent_name:
                    self.agent = agent
                    return self.agent

            self.agent = self.agent_client.create_agent(
                model=MODEL_DEPLOYMENT_NAME,
                name=sql_query_generator_agent_name,
                instructions=sql_query_generator_instruction,
                top_p=0.89,
                temperature=0.01
            )
            return self.agent

    def invoke(self, prompt: str) -> str:
        logger.info(f"Invoking SQL agent for prompt: {prompt}")
        thread = None
        try:
            agent = self.get_or_create_sql_agent()
            instruction = build_sql_instruction() + "\n\nIMPORTANT: Output ONLY the SQL query. Do NOT include any explanations, descriptions, or additional text."

            thread = self.agent_client.threads.create()
            self.mark_run_active(thread.id)

            self.agent_client.messages.create(
                thread_id=thread.id,
                role="assistant",
                content=instruction
            )

            self.agent_client.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )

            run = self.agent_client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=agent.id
            )

            messages = list(self.agent_client.messages.list(
                thread_id=thread.id,
                order=ListSortOrder.ASCENDING
            ))

            agent_response = None
            for message in reversed(messages):
                if message.role == MessageRole.AGENT and message.text_messages:
                    agent_response = message.text_messages[-1].text.value
                    break

            if agent_response is None:
                raise RuntimeError("No response from SQL agent")

            return self.extract_sql_query(agent_response)

        except Exception as e:
            logger.error("Error during SQL agent invocation", exc_info=True)
            raise RuntimeError(f"SQL generation failed: {e}")
        finally:
            if thread:
                self.remove_run(thread.id)

            if datetime.now() - self.last_cleanup > self.cleanup_interval:
                self.cleanup_stale_runs()
                self.last_cleanup = datetime.now()

    def extract_sql_query(self, response: str) -> str:
        """Ensure only valid SQL is returned"""
        # Reject any code that isn't SQL
        if "import matplotlib" in response or "plt." in response:
            logger.error("Rejected non-SQL code generation")
            raise ValueError("Only SQL queries should be generated")
    
        if "SELECT" in response and "FROM" in response and "```" not in response:
            return response.strip()

        if "```sql" in response:
            start_idx = response.find("```sql") + len("```sql")
            end_idx = response.find("```", start_idx)
            if end_idx != -1:
                return response[start_idx:end_idx].strip()

        if "```" in response:
            parts = response.split("```")
            if len(parts) >= 3:
                return parts[1].strip()

        logger.warning("Could not cleanly extract SQL query from response. Returning full response.")
        return response

    # --- THREAD CLEANUP SUPPORT METHODS ---

    def mark_run_active(self, thread_id):
        self.active_runs[thread_id] = datetime.now()

    def remove_run(self, thread_id):
        self.active_runs.pop(thread_id, None)

    def get_active_thread_ids(self):
        return set(self.active_runs.keys())

    def cleanup_stale_runs(self, ttl_minutes=60):
        now = datetime.now()
        stale_threshold = now - timedelta(minutes=ttl_minutes)
        before_count = len(self.active_runs)
        self.active_runs = {
            tid: ts for tid, ts in self.active_runs.items()
            if ts >= stale_threshold
        }
        after_count = len(self.active_runs)
        if before_count != after_count:
            logger.info(f"Cleaned up stale AGSQLQueryGenerator runs: {before_count - after_count} removed")
