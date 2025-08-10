#graph_utils.py
import pandas as pd
import re
from datetime import datetime, timedelta
from . import config
import logging
from .config import (
    DATABRICKS_SERVER_HOSTNAME,
    DATABRICKS_ACCESS_TOKEN,
    DATABRICKS_HTTP_PATH
)
from .schema_utils import load_schema

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with higher level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def infer_y_axis_column(prompt: str, df: pd.DataFrame) -> str:
    logger.info("🚀 infer_y_axis_column")
    prompt_lower = prompt.lower()
    for col in df.columns:
        if col != "deal_num" and col in prompt_lower:
            return col
    return "total_realized_pnl"

def infer_chart_type(prompt: str) -> str:
    logger.info("🚀 infer_chart_type")
    if "line" in prompt.lower():
        return "line"
    elif "pie" in prompt.lower():
        return "pie"
    else: 
        return "bar"
    

def infer_top_n(prompt: str, default: int = 10) -> int:
    logger.info("🚀 infer_top_n")
    match = re.search(r"top\s+(\d+)", prompt.lower())
    if match:
        return int(match.group(1))
    return default

def apply_prompt_filters(df: pd.DataFrame, prompt: str) -> pd.DataFrame:
    logger.info("🚀 apply_prompt_filters")

    prompt_lower = prompt.lower()

    # Filter by trader
    for trader in df['trader'].dropna().unique():
        if trader.lower() in prompt_lower:
            df = df[df['trader'].str.lower() == trader.lower()]
            break

    # Filter by counterparty
    for cp in df['counterparty'].dropna().unique():
        if cp.lower() in prompt_lower:
            df = df[df['counterparty'].str.lower() == cp.lower()]
            break

    # Filter by month/year
    if "july" in prompt_lower:
        df = df[df['latest_trade_date'].dt.month == 7]
    elif "2025" in prompt_lower:
        df = df[df['latest_trade_date'].dt.year == 2025]

    return df

# Parse common natural language time filters from the prompt
def apply_time_filter(df, prompt):
    logger.info("🚀 apply_time_filter")
    now = datetime.now()

    # Ensure latest_trade_date is datetime
    if 'latest_trade_date' not in df.columns:
        return df

    df = df.copy()

    # Filter for "last month"
    if re.search(r'\blast month\b', prompt, re.IGNORECASE):
        first_day_of_current_month = now.replace(day=1)
        last_month_end = first_day_of_current_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return df[(df['latest_trade_date'] >= last_month_start) & (df['latest_trade_date'] <= last_month_end)]

    # Filter for specific month like "July"
    match = re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b', prompt, re.IGNORECASE)
    if match:
        month_str = match.group(1)
        month_number = datetime.strptime(month_str, "%B").month
        return df[df['latest_trade_date'].dt.month == month_number]

    # Filter for "Q1", "Q2", "Q3", "Q4"
    match = re.search(r'\bQ([1-4])\b', prompt, re.IGNORECASE)
    if match:
        quarter = int(match.group(1))
        start_month = 3 * (quarter - 1) + 1
        end_month = start_month + 2
        return df[df['latest_trade_date'].dt.month.isin(range(start_month, end_month + 1))]

    # Default: no filter
    return df

