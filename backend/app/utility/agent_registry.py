# backend/app/utility/agent_registry.py

REGISTERED_AGENT_INSTANCES = {}

def register_agent_instance(agent_name: str, agent_instance):
    REGISTERED_AGENT_INSTANCES[agent_name] = agent_instance

def get_agent_instance(agent_name: str):
    return REGISTERED_AGENT_INSTANCES.get(agent_name)
