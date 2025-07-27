#tools.py

###labs
import json
from pathlib import Path
import uuid
from typing import Any, Callable, Set
import ssl
import urllib3
from databricks import sql
import pandas as pd
import numpy as np
from . import config
from typing import Any, Dict, List, Optional, Tuple

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

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

# def get_deals_data(query: str) -> str:
#      result = {"columns": ["id", "value"], "data": [{"id":1,"value":100}]}
#      return json.dumps(result)

# Function to get data from databricks
def get_deals_data() -> dict:
    """
    Fetch deals data from databricks delta table.
    Converts datetime columns and NaNs for JSON serialization.
    :param query: the query to execute on databricks.
    :return: dict: {'columns': list, 'data': list of records}
    """
    try:
        df = read_data_from_delta(config.query)

        # Convert NaN to None for JSON serialization
        df = df.replace({np.nan: None})

        # Convert datetime columns to ISO string
        for col in df.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns:
            df[col] = df[col].astype(str)

        return {
            "columns": df.columns.tolist(),
            "data": df.to_dict('records')
        }

    except Exception as e:
        print(f"Error in get_deals_data: {str(e)}")
        return {"error": str(e)}

   

# Get data from databricks delta tables
def read_data_from_delta(query: str) -> pd.DataFrame:
    """
    Read data from Delta table with proper resource handling
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise ConnectionError("Failed to establish database connection")
            
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        return pd.DataFrame(data, columns=columns)
        
    finally:
        if conn:
            conn.close()
            

#--- Database Connection Handling ---
def get_db_connection():
    """Create and return a database connection with error handling"""
    try:
        return sql.connect(
            server_hostname=config.DATABRICKS_SERVER_HOSTNAME,
            http_path=config.DATABRICKS_HTTP_PATH,
            access_token=config.DATABRICKS_ACCESS_TOKEN,
            _verify_ssl=False
        )
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return None

from typing import Dict, Any

# def generate_graph_data(prompt: str) -> Dict[str, Any]:
#     """
#     This function generates graph data based on a specific user prompt.
#     It should parse the prompt and return a structured format that the frontend expects.
#     """
#     if "monthly pnl" in prompt.lower():
#         return {
#             "graph": {
#                 "type": "bar",
#                 "title": "Monthly PnL",
#                 "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
#                 "values": [12000, 15000, 13000, 17000, 16000, 18000]
#             }
#         }
#     elif "deal volume" in prompt.lower():
#         return {
#                 "type": "bar",
#                 "title": "Deal Volumes",
#                 "labels": ["Deal A", "Deal B", "Deal C"],
#                 "values": [300, 400, 500]
#             }
#     else:
#         raise ValueError("Unable to generate graph data from prompt")

def generate_graph_data(prompt: str) -> Dict[str, Any]:
    """
    Robust graph data generator with dtype handling and fallbacks
    """
    try:
        deals_data = get_deals_data()
        
        if "error" in deals_data:
            return {
                "response": "Unable to fetch deals data. Please try again later.",
                "error": deals_data["error"]
            }
        
        df = pd.DataFrame(deals_data['data'])
        
        # Clean and convert numeric columns
        numeric_cols = []
        for col in df.columns:
            try:
                # Try converting to numeric, coercing errors to NaN
                df[col] = pd.to_numeric(df[col], errors='coerce')
                if not df[col].isna().all():  # Only keep if we got some numbers
                    numeric_cols.append(col)
            except:
                continue
        
        if not numeric_cols:
            return {
                "response": "No numeric data available for visualization.",
                "suggested_action": "fetch_raw_data"
            }
        
        # Handle specific requests with proper dtype checking
        if "realized value" in prompt.lower():
            target_col = 'ltd_realized_value'
            if target_col in numeric_cols:
                # Aggregate by deal_num first
                deal_aggregates = df.groupby('deal_num')[target_col].sum().reset_index()
                top_deals = deal_aggregates.nlargest(5, target_col)
                
                return {
                    "response": "Top deals by realized value:",
                    "graph_data": {
                        "type": "bar",
                        "title": "Top Deals by Realized Value",
                        "labels": top_deals['deal_num'].astype(str).tolist(),
                        "values": top_deals[target_col].tolist(),
                        "dataset_label": "Realized Value (USD)"
                    }
            }
            else:
                return {
                    "response": f"Column '{target_col}' not available or not numeric. Available numeric columns: {', '.join(numeric_cols)}",
                    "suggested_action": "show_available_columns"
                }
        
        # Fallback to first available numeric column
        fallback_col = numeric_cols[0]
        clean_df = df.dropna(subset=[fallback_col])
        sample_data = clean_df.nlargest(5, fallback_col)
        
        return {
            "response": f"Showing data for {fallback_col.replace('_', ' ')} (fallback):",
            "graph_data": {
                "type": "bar",
                "title": f"Top Deals by {fallback_col.replace('_', ' ')}",
                "labels": sample_data['deal_num'].astype(str).tolist(),
                "values": sample_data[fallback_col].tolist()
            }
        }
        
    except Exception as e:
        return {
            "response": f"Failed to generate graph: {str(e)}",
            "error": str(e),
            "suggested_action": "fetch_raw_data"
        }

# Define a set of callable functions
user_functions: Set[Callable[..., Any]] = {
    submit_support_ticket, get_deals_data
}