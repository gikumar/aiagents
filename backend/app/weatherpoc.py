import os
import time
import json
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionTool

# 1. Define your custom function tool
def fetch_weather(location: str) -> str:
    """
    Fetch the weather information for the specified location.
    :param location: The location name (e.g. "London").
    :return: JSON string with weather summary.
    """
    # mock or real call
    data = {"London": "Cloudy, 18°C", "New York": "Sunny, 25°C"}
    weather = data.get(location, "Weather data not available")
    return json.dumps({"weather": weather})

user_functions = {fetch_weather}

# 2. Create client, tool definitions, and agent
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential()
)

functions = FunctionTool(functions=user_functions)

with project_client:
    agent = project_client.agents.create_agent(
        model=model_deployment,
        name="weather-agent",
        instructions="You are a helpful agent. When needed, use fetch_weather.",
        tools=functions.definitions
    )
    print(f"Agent created, ID = {agent.id}")

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
        if run.status == "requires_action":
            calls = run.required_action.submit_tool_outputs.tool_calls
            outputs = []
            for call in calls:
                if call.name == "fetch_weather":
                    result = fetch_weather("London")
                    outputs.append({"tool_call_id": call.id, "output": result})
            project_client.agents.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=outputs)

    print("Final status:", run.status)

    # 4. Retrieve complete message thread
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for msg in messages:
        print(f"{msg['role']}: {msg['content']}")

    project_client.agents.delete_agent(agent.id)
