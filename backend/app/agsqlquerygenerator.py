import threading
import traceback
import logging

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from .configagsqlquerygenerator import (
    PROJECT_ENDPOINT,
    MODEL_DEPLOYMENT_NAME,
    sql_query_generator_agent_name,
    sql_query_generator_instruction
)
from .sql_query_generator_instruction import build_sql_instruction
from azure.ai.agents.models import ListSortOrder, MessageRole


# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR, format='%(asctime)s [%(levelname)s] %(message)s')


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

    def get_or_create_sql_agent(self):
        if self.agent is not None:
            logger.info("Returning cached SQL agent instance")
            return self.agent

        with AGSQLQueryGenerator._lock:
            if self.agent is not None:
                logger.info("Returning cached SQL agent instance after acquiring lock")
                return self.agent

            logger.info("Searching for existing SQL agent by name...")
            for agent in self.agent_client.list_agents():
                if agent.name == sql_query_generator_agent_name:
                    logger.info(f"Reusing existing SQL agent: {agent.name} ({agent.id})")
                    self.agent = agent
                    return self.agent

            logger.info(f"Creating new SQL agent: {sql_query_generator_agent_name}")
            self.agent = self.agent_client.create_agent(
                model=MODEL_DEPLOYMENT_NAME,
                name=sql_query_generator_agent_name,
                instructions=sql_query_generator_instruction,
                top_p=0.1,
                temperature=0.7
            )
            logger.info(f"Created new SQL agent: {self.agent.name} ({self.agent.id})")
            return self.agent

    def invoke(self, prompt: str) -> str:
        logger.info(f"Invoking SQL agent for prompt: {prompt}")
        try:
            agent = self.get_or_create_sql_agent()
            # Add clear directive to output ONLY the SQL query
            instruction = build_sql_instruction() + "\n\nIMPORTANT: Output ONLY the SQL query. Do NOT include any explanations, descriptions, or additional text."
            
            # Create a new thread
            thread = self.agent_client.threads.create()
            
            # Add instruction as assistant message
            self.agent_client.messages.create(
                thread_id=thread.id,
                role="assistant",
                content=instruction
            )
            
            # Add user prompt
            self.agent_client.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            # Create and process run
            run = self.agent_client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=agent.id
            )
            
            # Get the agent response
            messages = list(self.agent_client.messages.list(
                thread_id=thread.id,
                order=ListSortOrder.ASCENDING
            ))
            
            # Find the last agent message
            agent_response = None
            for message in reversed(messages):
                if message.role == MessageRole.AGENT and message.text_messages:
                    agent_response = message.text_messages[-1].text.value
                    break
            
            if agent_response is None:
                raise RuntimeError("No response from SQL agent")
            
            # Extract SQL query from the response
            sql_query = self.extract_sql_query(agent_response)
            return sql_query
            
        except Exception as e:
            logger.error("Error during SQL agent invocation", exc_info=True)
            raise RuntimeError(f"SQL generation failed: {e}")

    def extract_sql_query(self, response: str) -> str:
        """Extracts SQL query from agent response, removing any surrounding text or markdown formatting."""
        # Case 1: Response is already a clean SQL query
        if "SELECT" in response and "FROM" in response and "```" not in response:
            return response.strip()
        
        # Case 2: Response contains markdown code block
        if "```sql" in response:
            start_idx = response.find("```sql") + len("```sql")
            end_idx = response.find("```", start_idx)
            if end_idx != -1:
                return response[start_idx:end_idx].strip()
        
        # Case 3: Generic code block without language specification
        if "```" in response:
            parts = response.split("```")
            if len(parts) >= 3:
                return parts[1].strip()
        
        # Fallback: Return entire response with a warning
        logger.warning("Could not cleanly extract SQL query from response. Returning full response.")
        return response