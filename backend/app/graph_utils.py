import pandas as pd
import re

def infer_y_axis_column(prompt: str, df: pd.DataFrame) -> str:
    prompt_lower = prompt.lower()
    for col in df.columns:
        if col != "deal_num" and col in prompt_lower:
            return col
    return "total_realized_pnl"

def infer_chart_type(prompt: str) -> str:
    if "line" in prompt.lower():
        return "line"
    return "bar"

def infer_top_n(prompt: str, default: int = 10) -> int:
    match = re.search(r"top\s+(\d+)", prompt.lower())
    if match:
        return int(match.group(1))
    return default

def apply_prompt_filters(df: pd.DataFrame, prompt: str) -> pd.DataFrame:
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
