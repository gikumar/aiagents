import json
import time
from pathlib import Path
import uuid
import ssl
import urllib3
from databricks import sql
import pandas as pd
import numpy as np
import re
from typing import Any, Callable, Set, Dict, List, Optional
from . import config
from .graph_utils import (
    infer_chart_type,
    infer_top_n,
    apply_prompt_filters,
    apply_time_filter,
    prompt_to_sql
)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# Support ticket submission
def submit_support_ticket(email_address: str, description: str) -> str:
    script_dir = Path(__file__).parent
    ticket_number = str(uuid.uuid4()).replace('-', '')[:6]
    file_name = f"ticket-{ticket_number}.txt"
    file_path = script_dir / file_name
    text = f"Support ticket: {ticket_number}\nSubmitted by: {email_address}\nDescription:\n{description}"
    file_path.write_text(text)
    return json.dumps({"message": f"Support ticket {ticket_number} submitted. The ticket file is saved as {file_name}"})

# DB Connection
def get_db_connection():
    max_retries = 3
    retry_delay = 1
    for attempt in range(max_retries):
        try:
            return sql.connect(
                server_hostname=config.DATABRICKS_SERVER_HOSTNAME,
                http_path=config.DATABRICKS_HTTP_PATH,
                access_token=config.DATABRICKS_ACCESS_TOKEN,
                _verify_ssl=False,
                timeout=30
            )
        except Exception as e:
            if attempt == max_retries - 1:
                raise ConnectionError(f"Database connection failed after {max_retries} attempts: {str(e)}")
            time.sleep(retry_delay * (attempt + 1))

# Read data from delta table
def read_data_from_delta(query: str) -> pd.DataFrame:
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns) if data else pd.DataFrame(columns=columns)
    except Exception as e:
        raise RuntimeError(f"Error executing query: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                print(f"Warning: Error closing connection: {str(e)}")

# Get deals data from config.query
def get_deals_data() -> dict:
    try:
        df = read_data_from_delta(config.query)
        df = df.replace({np.nan: None})
        for col in df.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns:
            df[col] = df[col].astype(str)
        return {"columns": df.columns.tolist(), "data": df.to_dict('records')}
    except Exception as e:
        return {"error": str(e)}

# Get aggregated data from prompt
def get_deals_aggrgated_data(prompt: str = None) -> dict:
    try:
        query_to_execute = prompt_to_sql(prompt)
        df = read_data_from_delta(query_to_execute)
        if df.empty:
            return {"columns": [], "data": [], "warning": "Query returned no results"}

        for col in ['total_realized_pnl', 'total_unrealized_pnl', 'total_pnl', 'total_quantity', 'avg_price']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        if 'latest_trade_date' in df.columns:
            df['latest_trade_date'] = pd.to_datetime(df['latest_trade_date'], errors='coerce')

        return {
            "columns": df.columns.tolist(),
            "data": df.replace({np.nan: None}).to_dict('records'),
            "query_used": query_to_execute[:100] + "..." if len(query_to_execute) > 100 else query_to_execute
        }

    except Exception as e:
        return {
            "error": f"Error in get_deals_data: {str(e)}",
            "query_attempted": config.graphquery
        }

# Generate chart from prompt
def generate_graph_data(prompt: str) -> dict:
    try:
        result = get_deals_aggrgated_data(prompt)

        if 'error' in result:
            return {"response": f"Graph generation failed: {result['error']}", "error": result['error']}
        elif not result['data']:
            return {"response": "No data available to generate graph.", "warning": result.get('warning', '')}

        df = pd.DataFrame(result['data'])

        if 'latest_trade_date' in df.columns:
            df['latest_trade_date'] = pd.to_datetime(df['latest_trade_date'], errors='coerce')

        df = apply_prompt_filters(df, prompt)
        df = apply_time_filter(df, prompt)

        if df.empty:
            return {"response": "Filtered data is empty. Please revise your prompt or try different filters."}

        return generate_default_graph(df, prompt)

    except Exception as e:
        return {"response": f"Graph generation failed: {str(e)}", "error": str(e)}

# Basic text summarizer
def get_insights_from_text(text_content: str) -> dict:
    preview = text_content[:500] + "..." if len(text_content) > 500 else text_content
    return {
        "summary": f"Received text content with length {len(text_content)} characters.",
        "preview": preview
    }

# Exposed functions
user_functions: Set[Callable[..., Any]] = {
    submit_support_ticket,
    get_deals_data,
    get_insights_from_text,
    generate_graph_data
}

# Utility: Infer top N
def infer_top_n(prompt: str, default: int = 10) -> int:
    match = re.search(r"top\s+(\d+)", prompt.lower())
    return int(match.group(1)) if match else default

# Default graph generation

def generate_default_graph(df: pd.DataFrame, prompt: str = "") -> Dict[str, Any]:
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

    y_col = "total_realized_pnl"
    for keyword, column in y_axis_candidates.items():
        if keyword in prompt.lower() and column in df.columns:
            y_col = column
            break

    if y_col not in df.columns:
        return {"response": f"Column '{y_col}' not found in data", "error": "Invalid column for Y-axis"}

    chart_type = infer_chart_type(prompt)
    dataset_label = y_col.replace("_", " ").title()

    x_col = "deal_num"
    for candidate in ['counterparty', 'trader', 'deal_type', 'instrument_type']:
        if candidate in prompt.lower() and candidate in df.columns:
            x_col = candidate
            break
    else:
        if chart_type == "pie" and 'counterparty' in df.columns:
            x_col = 'counterparty'

    top_n = infer_top_n(prompt)

    if chart_type == "pie":
        pie_df = df.groupby(x_col, as_index=False)[y_col].sum()
        pie_df = pie_df.sort_values(by=y_col, ascending=False).head(top_n)
        return {
            "response": f"{dataset_label} by {x_col.title()}",
            "graph_data": {
                "type": "pie",
                "title": f"{dataset_label} by {x_col.title()}",
                "labels": pie_df[x_col].astype(str).tolist(),
                "values": pie_df[y_col].tolist(),
                "dataset_label": dataset_label
            }
        }

    df = df.sort_values(by=y_col, ascending=False).head(top_n)
    return {
        "response": f"{dataset_label} by {x_col.title()}",
        "graph_data": {
            "type": chart_type,
            "title": f"{dataset_label} by {x_col.title()}",
            "labels": df[x_col].astype(str).tolist(),
            "values": df[y_col].tolist(),
            "dataset_label": dataset_label
        }
    }
