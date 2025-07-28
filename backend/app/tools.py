#tools.py

import json
import time
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
def get_deals_data(query: str = None) -> dict:
    """
    Fetch deals data from databricks delta table.
    Converts datetime columns and NaNs for JSON serialization.
    
    Args:
        query: Optional custom query to execute. If None, uses default query from config.
        
    Returns:
        dict: {'columns': list, 'data': list of records} or {'error': str} on failure
    """
    try:
        # Use custom query if provided, otherwise fall back to config.query
        query_to_execute = query if query is not None else config.query
        
        if not query_to_execute or not query_to_execute.strip():
            raise ValueError("No query provided to execute")
            
        df = read_data_from_delta(query_to_execute)
        
        if df.empty:
            return {
                "columns": [],
                "data": [],
                "warning": "Query returned no results"
            }
                
        # Data cleaning and preparation
        df = (
            df
            # Convert NaN/NaT to None for JSON serialization
            .replace({np.nan: None, pd.NaT: None})
            # Convert datetime columns to ISO strings
            .pipe(lambda df: df.assign(**{
                col: df[col].astype(str)
                for col in df.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns
            }))
        )

        return {
            "columns": df.columns.tolist(),
            "data": df.to_dict('records'),
            "query_used": query_to_execute  # For debugging/tracking
        }

    except Exception as e:
        error_msg = f"Error in get_deals_data: {str(e)}"
        print(error_msg)
        return {
            "error": error_msg,
            "query_attempted": query if query is not None else config.query
        }

   

# Get data from databricks delta tables
def read_data_from_delta(query: str) -> pd.DataFrame:
    """
    Read data from Delta table with proper resource handling and error management
    
    Args:
        query: SQL query to execute
        
    Returns:
        pd.DataFrame: Resultset as a DataFrame
        
    Raises:
        ValueError: If query is empty or connection fails
        RuntimeError: If query execution fails
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise ConnectionError("Failed to establish database connection")
            
        with conn.cursor() as cursor:
            cursor.execute(query)
            
            # Get column names from cursor description
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            
            if not data:
                return pd.DataFrame(columns=columns)
                
            return pd.DataFrame(data, columns=columns)
            
    except Exception as e:
        error_msg = f"Error executing query: {str(e)}"
        print(error_msg)
        raise RuntimeError(error_msg)
        
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                print(f"Warning: Error closing connection: {str(e)}")
           

#--- Database Connection Handling ---
def get_db_connection():
    """Create and return a database connection with enhanced error handling"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            return sql.connect(
                server_hostname=config.DATABRICKS_SERVER_HOSTNAME,
                http_path=config.DATABRICKS_HTTP_PATH,
                access_token=config.DATABRICKS_ACCESS_TOKEN,
                _verify_ssl=False,
                timeout=30  # Added connection timeout
            )
        except Exception as e:
            if attempt == max_retries - 1:
                raise ConnectionError(f"Database connection failed after {max_retries} attempts: {str(e)}")
            time.sleep(retry_delay * (attempt + 1))
    
    raise ConnectionError("Unexpected error in get_db_connection")
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

def get_deals_data(query: str = None) -> dict:
    """
    Fetches deals data using the pre-aggregated graph query from config
    """
    try:
        # Use the graph query from config by default
        query_to_execute = query if query else config.graphquery
        
        if not query_to_execute or not query_to_execute.strip():
            raise ValueError("No query provided to execute")
            
        df = read_data_from_delta(query_to_execute)
        
        if df.empty:
            return {"columns": [], "data": [], "warning": "Query returned no results"}
            
        # Convert numeric columns and handle NULLs
        numeric_cols = [
            'total_realized_pnl', 'total_unrealized_pnl', 
            'total_pnl', 'total_quantity', 'avg_price'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert dates to strings for JSON serialization
        if 'latest_trade_date' in df.columns:
            df['latest_trade_date'] = pd.to_datetime(df['latest_trade_date']).astype(str)
        
        return {
            "columns": df.columns.tolist(),
            "data": df.replace({np.nan: None}).to_dict('records'),
            "query_used": query_to_execute[:100] + "..." if len(query_to_execute) > 100 else query_to_execute
        }

    except Exception as e:
        return {
            "error": f"Error in get_deals_data: {str(e)}",
            "query_attempted": query if query else config.graphquery
        }


def generate_graph_data(prompt: str) -> Dict[str, Any]:
    """
    Generates visualizations from the aggregated graph query results
    """
    try:
        deals_data = get_deals_data()
        
        if "error" in deals_data:
            return {
                "response": "Failed to fetch aggregated deals data",
                "error": deals_data["error"]
            }
            
        df = pd.DataFrame(deals_data['data'])
        
        # Handle different prompt types
        if "realized" in prompt.lower():
            return generate_realized_pnl_graph(df)
        elif "unrealized" in prompt.lower():
            return generate_unrealized_pnl_graph(df)
        elif "trend" in prompt.lower() or "over time" in prompt.lower():
            return generate_trend_graph(df)
        elif "compare" in prompt.lower():
            return generate_comparison_graph(df)
        else:
            #return generate_default_graph(df)
            return generate_default_graph(df, prompt)

    except Exception as e:
        return {
            "response": f"Graph generation failed: {str(e)}",
            "error": str(e)
        }

def generate_default_graph(df: pd.DataFrame, prompt: str = "") -> Dict[str, Any]:
    """
    Generate a default graph based on deal_num on x-axis and a dynamically chosen y-axis column from prompt.
    """
    y_axis_candidates = {
        "realized": "total_realized_pnl",
        "unrealized": "total_unrealized_pnl",
        "pnl": "total_pnl",
        "quantity": "total_quantity",
        "price": "avg_price",
        "payment": "total_payment_value",
        "cashflow": "cashflow_type_count",
        "count": "transaction_count"
    }

    y_column = "total_realized_pnl"  # default fallback
    for keyword, column in y_axis_candidates.items():
        if keyword in prompt.lower() and column in df.columns:
            y_column = column
            break

    if y_column not in df.columns:
        return {
            "response": f"Column '{y_column}' not found in data",
            "error": "Invalid column for Y-axis"
        }

    df = df.sort_values(by=y_column, ascending=False).head(15)

    return {
        "response": f"Deals graph by {y_column.replace('_', ' ').title()}",
        "graph_data": {
            "type": "bar",
            "title": f"Top Deals by {y_column.replace('_', ' ').title()}",
            "labels": df['deal_num'].astype(str).tolist(),
            "values": df[y_column].tolist(),
            "dataset_label": y_column.replace('_', ' ').title()
        }
    }



def generate_realized_pnl_graph(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate bar chart of top deals by realized PnL"""
    top_deals = df.nlargest(10, 'total_realized_pnl')
    
    return {
        "response": "Top deals by realized PnL",
        "graph_data": {
            "type": "bar",
            "title": "Realized PnL by Deal",
            "labels": top_deals['deal_num'].astype(str).tolist(),
            "values": top_deals['total_realized_pnl'].tolist(),
            "dataset_label": "Realized PnL (USD)"
        }
    }


def generate_trend_graph(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate proper time-series line chart from the aggregated data"""
    try:
        # Ensure we have the required columns
        if 'latest_trade_date' not in df.columns:
            raise ValueError("Missing date column for trend analysis")
            
        # Convert and sort by date
        df['date'] = pd.to_datetime(df['latest_trade_date'])
        df = df.sort_values('date')
        
        # Group by date (daily frequency)
        df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
        grouped = df.groupby('date_str').agg({
            'total_realized_pnl': 'sum',
            'total_unrealized_pnl': 'sum',
            'total_pnl': 'sum'
        }).reset_index()
        
        # Create line chart dataset
        return {
            "response": "PnL Trend Over Time",
            "graph_data": {
                "type": "line",
                "title": "Daily PnL Trend",
                "labels": grouped['date_str'].tolist(),
                "datasets": [
                    {
                        "label": "Realized PnL",
                        "data": grouped['total_realized_pnl'].tolist(),
                        "borderColor": "rgba(75, 192, 192, 1)",
                        "tension": 0.1
                    },
                    {
                        "label": "Total PnL",
                        "data": grouped['total_pnl'].tolist(),
                        "borderColor": "rgba(54, 162, 235, 1)",
                        "tension": 0.1
                    }
                ],
                "options": {
                    "scales": {
                        "y": {
                            "beginAtZero": False,
                            "title": {
                                "display": True,
                                "text": "USD Value"
                            }
                        },
                        "x": {
                            "title": {
                                "display": True,
                                "text": "Trade Date"
                            }
                        }
                    }
                }
            }
        }
        
    except Exception as e:
        return {
            "response": f"Could not generate trend graph: {str(e)}",
            "error": str(e)
        }


def generate_comparison_graph(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comparison of multiple PnL metrics"""
    top_deals = df.nlargest(10, 'total_pnl')
    
    return {
        "response": "Comparison of PnL Metrics",
        "graph_data": {
            "type": "bar",
            "title": "PnL Comparison by Deal",
            "labels": top_deals['deal_num'].astype(str).tolist(),
            "datasets": [
                {
                    "label": "Realized",
                    "data": top_deals['total_realized_pnl'].tolist(),
                    "backgroundColor": "rgba(54, 162, 235, 0.7)"
                },
                {
                    "label": "Unrealized",
                    "data": top_deals['total_unrealized_pnl'].tolist(),
                    "backgroundColor": "rgba(255, 99, 132, 0.7)"
                }
            ]
        }
    }

def get_insights_from_text(text_content: str) -> dict:
    # For now, a simple placeholder that returns length and preview
    preview = text_content[:500] + "..." if len(text_content) > 500 else text_content
    return {
        "summary": f"Received text content with length {len(text_content)} characters.",
        "preview": preview
    }

# Define a set of callable functions
user_functions: Set[Callable[..., Any]] = {
    submit_support_ticket, get_deals_data, get_insights_from_text
}