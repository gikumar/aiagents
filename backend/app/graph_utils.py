import pandas as pd
import re
import logging
from datetime import datetime, timedelta
from . import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def infer_y_axis_column(prompt: str, df: pd.DataFrame) -> str:
    prompt_lower = prompt.lower()
    for col in df.columns:
        if col != "deal_num" and col in prompt_lower:
            logger.debug(f"Inferred Y-axis column from prompt: {col}")
            return col
    logger.debug("Defaulting to 'total_realized_pnl' for Y-axis column")
    return "total_realized_pnl"


def infer_chart_type(prompt: str) -> str:
    prompt_lower = prompt.lower()
    if "line" in prompt_lower:
        logger.debug("Inferred chart type: line")
        return "line"
    elif "pie" in prompt_lower:
        logger.debug("Inferred chart type: pie")
        return "pie"
    else:
        logger.debug("Defaulting chart type: bar")
        return "bar"


def infer_top_n(prompt: str, default: int = 10) -> int:
    match = re.search(r"top\\s+(\\d+)", prompt.lower())
    if match:
        val = int(match.group(1))
        logger.debug(f"Inferred top N: {val}")
        return val
    logger.debug(f"Using default top N: {default}")
    return default


def apply_prompt_filters(df: pd.DataFrame, prompt: str) -> pd.DataFrame:
    prompt_lower = prompt.lower()
    logger.debug("Applying prompt filters")

    for trader in df['trader'].dropna().unique():
        if trader.lower() in prompt_lower:
            logger.debug(f"Filtering by trader: {trader}")
            df = df[df['trader'].str.lower() == trader.lower()]
            break

    for cp in df['counterparty'].dropna().unique():
        if cp.lower() in prompt_lower:
            logger.debug(f"Filtering by counterparty: {cp}")
            df = df[df['counterparty'].str.lower() == cp.lower()]
            break

    if "july" in prompt_lower:
        logger.debug("Filtering by July")
        df = df[df['latest_trade_date'].dt.month == 7]
    elif "2025" in prompt_lower:
        logger.debug("Filtering by year 2025")
        df = df[df['latest_trade_date'].dt.year == 2025]

    return df


def apply_time_filter(df, prompt):
    now = datetime.now()

    if 'latest_trade_date' not in df.columns:
        logger.warning("No 'latest_trade_date' column found")
        return df

    df = df.copy()
    prompt_lower = prompt.lower()

    if re.search(r'\\blast month\\b', prompt_lower):
        first_day = now.replace(day=1)
        last_month_end = first_day - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        logger.debug(f"Filtering for last month: {last_month_start} to {last_month_end}")
        return df[(df['latest_trade_date'] >= last_month_start) & (df['latest_trade_date'] <= last_month_end)]

    match = re.search(r'\\b(January|February|March|April|May|June|July|August|September|October|November|December)\\b', prompt, re.IGNORECASE)
    if match:
        month_str = match.group(1)
        month_number = datetime.strptime(month_str, "%B").month
        logger.debug(f"Filtering for month: {month_str} ({month_number})")
        return df[df['latest_trade_date'].dt.month == month_number]

    match = re.search(r'\\bQ([1-4])\\b', prompt, re.IGNORECASE)
    if match:
        quarter = int(match.group(1))
        start_month = 3 * (quarter - 1) + 1
        end_month = start_month + 2
        logger.debug(f"Filtering for quarter Q{quarter} ({start_month}-{end_month})")
        return df[df['latest_trade_date'].dt.month.isin(range(start_month, end_month + 1))]

    return df


def prompt_to_sql(prompt: str) -> str:
    prompt = prompt.lower()
    base_query = config.graphquery

    if "top 3" in prompt:
        base_query += " LIMIT 3;"
    elif "top 5" in prompt:
        base_query += " LIMIT 5;"
    elif "top 10" in prompt:
        base_query += " LIMIT 10;"
    else:
        base_query += ";"

    logger.debug(f"Generated SQL: {base_query}")
    return base_query
