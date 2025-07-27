#tools.py

###labs
import json
from pathlib import Path
import uuid
from typing import Any, Callable, Set

# Create a function to submit a support ticket
def submit_support_ticket(email_address: str, description: str) -> str:
    script_dir = Path(__file__).parent  # Get the directory of the script
    ticket_number = str(uuid.uuid4()).replace('-', '')[:6]
    file_name = f"ticket-{ticket_number}.txt"
    file_path = script_dir / file_name
    text = f"Support ticket: {ticket_number}\nSubmitted by: {email_address}\nDescription:\n{description}"
    file_path.write_text(text)

    message_json = json.dumps({"message": f"Support ticket {ticket_number} submitted. The ticket file is saved as {file_name}"})
    return message_json

# Define a set of callable functions
user_functions: Set[Callable[..., Any]] = {
    submit_support_ticket
}


##lab


# import pandas as pd
# import time
# import numpy as np
# import requests
# import json
# import os
# import ssl
# import urllib3
# import base64
# import io
# #from typing import Optional, Dict, Any, List

# #from promptflow import tool
# from functools import wraps
# import matplotlib.pyplot as plt

# from databricks import sql

# from openai import AzureOpenAI
# from azure.identity import DefaultAzureCredential
# from azure.ai.projects import AIProjectClient

# # #from azure.ai.agents import tool
# # from azure.ai.agents import tool
# # from azure.ai.agents import FunctionTool
# # from azure.ai.agents import CustomFunctionTool
# from azure.ai.agents.models import FunctionTool


# import os
# import time
# import json

# from . import config

# import datetime
# from datetime import datetime
# from typing import Any, Callable, Set, Dict, List, Optional
# from azure.ai.agents.tool import tool


# # Disable SSL warnings
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# ssl._create_default_https_context = ssl._create_unverified_context
# # tools.py
# import json

# # Create a function to submit a support ticket
# def submit_support_ticket(email_address: str, description: str) -> str:
#     script_dir = Path(__file__).parent  # Get the directory of the script
#     ticket_number = str(uuid.uuid4()).replace('-', '')[:6]
#     file_name = f"ticket-{ticket_number}.txt"
#     file_path = script_dir / file_name
#     text = f"Support ticket: {ticket_number}\nSubmitted by: {email_address}\nDescription:\n{description}"
#     file_path.write_text(text)

#     message_json = json.dumps({"message": f"Support ticket {ticket_number} submitted. The ticket file is saved as {file_name}"})
#     return message_json


# def fetch_weather(location: str) -> str:
#     return json.dumps({"weather": f"Temperature wise, it's nice in {location}."})

# def get_deals_data(query: str) -> str:
#     result = {"columns": ["id", "value"], "data": [{"id":1,"value":100}]}
#     return json.dumps(result)

# @tool
# def get_deals_data(query: str) -> dict:
#     """
#     Fetch deals data from databricks delata table
#     :param query: the query to exuecte on databricks.
#     :return: dict: {'columns': list, 'data': list of records}
#     """
#     try:
#         df = read_data_from_delta(query)

#         # Convert NaN to None for JSON serialization
#         df = df.replace({np.nan: None})
        
#         return {
#             "columns": df.columns.tolist(),
#             ## Increased to 100 for more data
#             #"data": df.head(100).to_dict('records')
#             "data": df.to_dict('records') 
#         }
#     except Exception as e:
#         print(f"Error in get_deals_data: {str(e)}")
#         return {"error": str(e)}
    

## Get data from databricks delta tables
# def read_data_from_delta(query: str) -> pd.DataFrame:
#     """
#     Read data from Delta table with proper resource handling
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         if not conn:
#             raise ConnectionError("Failed to establish database connection")
            
#         cursor = conn.cursor()
#         cursor.execute(query)
#         columns = [desc[0] for desc in cursor.description]
#         data = cursor.fetchall()
#         return pd.DataFrame(data, columns=columns)
        
#     finally:
#         if conn:
#             conn.close()
            

# --- Database Connection Handling ---
# def get_db_connection():
#     """Create and return a database connection with error handling"""
#     try:
#         return sql.connect(
#             server_hostname=config.DATABRICKS_SERVER_HOSTNAME,
#             http_path=config.DATABRICKS_HTTP_PATH,
#             access_token=config.DATABRICKS_ACCESS_TOKEN,
#             _verify_ssl=False
#         )
#     except Exception as e:
#         print(f"Database connection failed: {str(e)}")
#         return None
