# backend/app/utility/agent_registry.py

# Set up logger
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Create console handler with higher level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

REGISTERED_AGENT_INSTANCES = {}

def register_agent_instance(agent_name: str, agent_instance):
    logger.info(f"🚀agent registry: register_agent_instance: {agent_name}")
    REGISTERED_AGENT_INSTANCES[agent_name] = agent_instance

def get_agent_instance(agent_name: str):
    logger.info(f"🚀agent registry: get_agent_instance: {agent_name}")
    return REGISTERED_AGENT_INSTANCES.get(agent_name)
