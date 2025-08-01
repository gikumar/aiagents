# backend/app/tools.py
import json
import re
import os
from datetime import datetime, date
from typing import Dict, List, Optional
import pandas as pd
from databricks import sql
from .config import (
    DATABRICKS_SERVER_HOSTNAME,
    DATABRICKS_ACCESS_TOKEN,
    DATABRICKS_HTTP_PATH
)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def execute_databricks_query(sql_query: str) -> Dict:
    """Execute SQL query against Databricks SQL Warehouse"""
    if not all([DATABRICKS_SERVER_HOSTNAME, DATABRICKS_ACCESS_TOKEN, DATABRICKS_HTTP_PATH]):
        return {
            "status": "error",
            "message": "Databricks connection details not configured",
            "query": sql_query
        }

    try:
        with sql.connect(
            server_hostname=DATABRICKS_SERVER_HOSTNAME,
            http_path=DATABRICKS_HTTP_PATH,
            access_token=DATABRICKS_ACCESS_TOKEN
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                columns = [desc[0] for desc in cursor.description]
                data = []
                for row in cursor.fetchall():
                    row_dict = {}
                    for idx, col in enumerate(columns):
                        if isinstance(row[idx], (datetime, date)):
                            row_dict[col] = row[idx].isoformat()
                        else:
                            row_dict[col] = row[idx]
                    data.append(row_dict)
                
                return {
                    "status": "success",
                    "columns": columns,
                    "data": data,
                    "query": sql_query,
                    "row_count": len(data)
                }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "query": sql_query,
            "error_type": type(e).__name__
        }

def get_insights_from_text(text_content: str) -> Dict:
    """
    Analyze text content and extract insights
    (Implementation matches what agentfactory.py expects)
    """
    if not text_content:
        return {
            "status": "error",
            "message": "No content provided"
        }

    try:
        # Basic text analysis - extend with your NLP logic
        word_count = len(text_content.split())
        char_count = len(text_content)
        line_count = len(text_content.splitlines())
        
        return {
            "status": "success",
            "insights": {
                "word_count": word_count,
                "character_count": char_count,
                "line_count": line_count,
                "content_start": text_content[:100] + "..." if len(text_content) > 100 else text_content
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def generate_graph_data(query_results: Dict, prompt: str) -> Dict:
    """Generate visualization data from query results"""
    if not query_results.get('data'):
        return {
            "status": "error",
            "message": "No data available for visualization",
            "query_results": query_results
        }

    try:
        df = pd.DataFrame(query_results['data'])
        
        # Apply filters from prompt
        if 'latest_trade_date' in df.columns:
            df = apply_time_filter(df, prompt)
        df = apply_prompt_filters(df, prompt)
        
        # Infer visualization parameters
        chart_type = infer_chart_type(prompt)
        y_axis = infer_y_axis_column(prompt, df)
        top_n = infer_top_n(prompt)
        
        # Prepare visualization spec
        return {
            "status": "success",
            "visualization": {
                "chart_type": chart_type,
                "x_axis": "trader" if "trader" in df.columns else df.columns[0],
                "y_axis": y_axis,
                "data": json.loads(df.to_json(orient='records', date_format='iso')),
                "top_n": top_n
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Graph generation failed: {str(e)}",
            "query_results": query_results
        }

# Graph utility functions (from graph_utils.py)
def infer_y_axis_column(prompt: str, df: pd.DataFrame) -> str:
    prompt_lower = prompt.lower()
    for col in df.columns:
        if col != "deal_num" and col in prompt_lower:
            return col
    return "total_realized_pnl"

def infer_chart_type(prompt: str) -> str:
    if "line" in prompt.lower():
        return "line"
    elif "pie" in prompt.lower():
        return "pie"
    else: 
        return "bar"

def infer_top_n(prompt: str, default: int = 10) -> int:
    match = re.search(r"top\s+(\d+)", prompt.lower())
    if match:
        return int(match.group(1))
    return default

def apply_prompt_filters(df: pd.DataFrame, prompt: str) -> pd.DataFrame:
    prompt_lower = prompt.lower()

    # Filter by trader
    if 'trader' in df.columns:
        for trader in df['trader'].dropna().unique():
            if trader.lower() in prompt_lower:
                df = df[df['trader'].str.lower() == trader.lower()]
                break

    # Filter by counterparty
    if 'counterparty' in df.columns:
        for cp in df['counterparty'].dropna().unique():
            if cp.lower() in prompt_lower:
                df = df[df['counterparty'].str.lower() == cp.lower()]
                break

    return df

def apply_time_filter(df: pd.DataFrame, prompt: str) -> pd.DataFrame:
    """Apply time filters from natural language prompt"""
    if 'latest_trade_date' not in df.columns:
        return df

    now = datetime.now()
    prompt_lower = prompt.lower()

    # Filter for "last month"
    if "last month" in prompt_lower:
        first_day = now.replace(day=1)
        last_month_end = first_day - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return df[(df['latest_trade_date'] >= last_month_start) & 
                  (df['latest_trade_date'] <= last_month_end)]

    # Month filter
    months = ['january','february','march','april','may','june',
              'july','august','september','october','november','december']
    for i, month in enumerate(months):
        if month in prompt_lower:
            return df[df['latest_trade_date'].dt.month == i+1]

    return df

# Maintain empty user_functions dict as expected by agentfactory.py
user_functions = {}