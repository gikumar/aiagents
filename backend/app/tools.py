#Sharing next file just keep it and do not analyze until i confirm I have shared all the files
# backend/app/tools.py

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
from typing import Any, Callable, Set, Dict, List

from . import config
from .schema_utils import load_schema
from .agsqlquerygenerator import AGSQLQueryGenerator
from .sql_query_generator_instruction import build_sql_instruction
from .graph_utils import (
    infer_chart_type,
    infer_top_n,
    apply_prompt_filters,
    apply_time_filter,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

schema_data = load_schema()
sql_generator = AGSQLQueryGenerator()

def submit_support_ticket(email_address: str, description: str) -> str:
    script_dir = Path(__file__).parent
    ticket_number = str(uuid.uuid4()).replace("-", "")[:6]
    file_path = script_dir / f"ticket-{ticket_number}.txt"
    file_path.write_text(f"Support ticket: {ticket_number}\nSubmitted by: {email_address}\nDescription:\n{description}")
    return json.dumps({"message": f"Support ticket {ticket_number} submitted. Saved as {file_path.name}"})

def get_db_connection():
    for attempt in range(3):
        try:
            return sql.connect(
                server_hostname=config.DATABRICKS_SERVER_HOSTNAME,
                http_path=config.DATABRICKS_HTTP_PATH,
                access_token=config.DATABRICKS_ACCESS_TOKEN,
                _verify_ssl=False,
                timeout=30,
            )
        except Exception as e:
            if attempt == 2:
                raise ConnectionError(f"Failed DB connection: {str(e)}")
            time.sleep((attempt + 1) * 1)

def read_data_from_delta(query: str) -> pd.DataFrame:
    if not query.strip():
        raise ValueError("Query cannot be empty")
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns) if data else pd.DataFrame(columns=columns)
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                print(f"Warning closing DB connection: {e}")

def get_deals_data(query: str) -> dict:
    if not query:
        return {"error": "Query is required"}
    try:
        df = read_data_from_delta(query)
        df = df.replace({np.nan: None})
        for col in df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
            df[col] = df[col].astype(str)
        return {"columns": df.columns.tolist(), "data": df.to_dict("records")}
    except Exception as e:
        return {"error": str(e)}

def get_deals_aggrgated_data(prompt: str) -> dict:
    try:
        query = call_sql_generator_with_validation(prompt)
        print(f"[Prompt]: {prompt}")
        print(f"[Generated SQL]: {query}")
        if not query.strip().lower().startswith("select"):
            raise ValueError("Invalid SQL: not a SELECT query")
        result = get_deals_data(query=query)
        result["query_used"] = query
        return result
    except Exception as e:
        return {"error": str(e), "query_attempted": query if "query" in locals() else None}

def generate_graph_data(prompt: str) -> dict:
    try:
        result = get_deals_aggrgated_data(prompt)
        if "error" in result:
            return {"response": f"Graph failed: {result['error']}", "error": result["error"]}
        elif not result["data"]:
            return {"response": "No data to generate graph.", "warning": result.get("warning", "")}
        df = pd.DataFrame(result["data"])
        if "latest_trade_date" in df.columns:
            df["latest_trade_date"] = pd.to_datetime(df["latest_trade_date"], errors="coerce")
        df = apply_prompt_filters(df, prompt)
        df = apply_time_filter(df, prompt)
        if df.empty:
            return {"response": "Filtered data is empty."}
        return generate_default_graph(df, prompt)
    except Exception as e:
        return {"response": f"Graph generation failed: {str(e)}", "error": str(e)}

def get_insights_from_text(text_content: str) -> dict:
    preview = text_content[:500] + "..." if len(text_content) > 500 else text_content
    return {"summary": f"Text length: {len(text_content)}", "preview": preview}

def infer_top_n(prompt: str, default: int = 10) -> int:
    match = re.search(r"top\s+(\d+)", prompt.lower())
    return int(match.group(1)) if match else default

def generate_default_graph(df: pd.DataFrame, prompt: str = "") -> Dict[str, Any]:
    y_axis_candidates = {
        "realized": "total_realized_pnl",
        "unrealized": "total_unrealized_pnl",
        "pnl": "total_pnl",
        "quantity": "total_quantity",
        "price": "avg_price",
        "payment": "total_payment_value",
        "cashflow": "cashflow_type_count",
        "count": "transaction_count",
    }
    y_col = next((col for keyword, col in y_axis_candidates.items() if keyword in prompt.lower() and col in df.columns), "total_realized_pnl")

    if y_col not in df.columns:
        return {"response": f"Missing Y-axis column: {y_col}", "error": "Invalid column for Y-axis"}

    chart_type = infer_chart_type(prompt)
    dataset_label = y_col.replace("_", " ").title()
    x_col = next((col for col in ["counterparty", "trader", "deal_type", "instrument_type"] if col in prompt.lower() and col in df.columns), "deal_num")
    if chart_type == "pie" and "counterparty" in df.columns:
        x_col = "counterparty"
    top_n = infer_top_n(prompt)

    if chart_type == "pie":
        if x_col not in df.columns:
            return {"response": f"Missing pie label column: {x_col}", "error": f"Missing column {x_col}"}
        pie_df = df.groupby(x_col, as_index=False)[y_col].sum().sort_values(by=y_col, ascending=False).head(top_n)
        return {
            "response": f"{dataset_label} by {x_col.title()}",
            "graph_data": {
                "type": "pie",
                "title": f"{dataset_label} by {x_col.title()}",
                "labels": pie_df[x_col].astype(str).tolist(),
                "values": pie_df[y_col].tolist(),
                "backgroundColor": [
                    "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
                    "#FF9F40", "#E7E9ED", "#76A346", "#D9534F", "#5BC0DE"
                ][:len(pie_df)],
                "dataset_label": dataset_label,
            },
        }

    df = df.sort_values(by=y_col, ascending=False).head(top_n)
    return {
        "response": f"{dataset_label} by {x_col.title()}",
        "graph_data": {
            "type": chart_type,
            "title": f"{dataset_label} by {x_col.title()}",
            "labels": df[x_col].astype(str).tolist(),
            "values": df[y_col].tolist(),
            "dataset_label": dataset_label,
        },
    }

def call_sql_generator_with_validation(prompt: str, max_retries=1) -> str:
    schema_data = load_schema()
    for attempt in range(max_retries + 1):
        sql = sql_generator.invoke(prompt)
        invalid = validate_sql_columns(sql, schema_data)
        if not invalid:
            return sql
        if attempt < max_retries:
            prompt += f"\n\nPlease remove or fix these columns: {', '.join(invalid)}"
        else:
            raise ValueError(f"Invalid columns in query: {invalid}")


def validate_sql_columns(sql_query: str, schema_data: dict) -> list:
    print("[DEBUG] Validating SQL query against schema...")
    print(f"[DEBUG] SQL Query: {sql_query}")
    used_columns = re.findall(r"\b(\w+)\.(\w+)\b", sql_query)
    print(f"[DEBUG] Extracted table.column references: {used_columns}")
    invalid_columns = []

    for table, col in used_columns:
        if table not in schema_data:
            print(f"[WARN] Table '{table}' not found in schema.")
            invalid_columns.append(f"{table}.{col}")
        elif col not in schema_data[table]:
            print(f"[WARN] Column '{col}' not found in table '{table}'.")
            invalid_columns.append(f"{table}.{col}")

    print(f"[DEBUG] Invalid columns found: {invalid_columns}")
    return list(set(invalid_columns))


user_functions: Set[Callable[..., Any]] = {
    submit_support_ticket,
    get_deals_data,
    get_insights_from_text,
    generate_graph_data,
    get_deals_aggrgated_data,
}