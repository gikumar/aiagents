#tools.py

import json

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