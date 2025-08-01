#Sharing next file just keep it and do not analyze until i confirm I have shared all the files
# backend/app/agsqlquerygenerator.py

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

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


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
            instruction = build_sql_instruction()
            logger.debug(f"Using instruction: {instruction}")

            result = self.agent_client.invoke_agent(
                agent_id=agent.id,
                input={
                    "prompt": prompt,
                    "instruction": instruction
                }
            )
            logger.info("SQL generation completed successfully")
            return result.output

        except Exception as e:
            logger.error("Error during SQL agent invocation", exc_info=True)
            raise RuntimeError(f"SQL generation failed: {e}")