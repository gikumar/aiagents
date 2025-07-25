# tools.py
import pandas as pd
from databricks import sql
from . import config
from promptflow import tool
import requests
import json
import os
import ssl
import urllib3
from openai import AzureOpenAI
from typing import Optional, Dict, Any, List
from functools import wraps
import time
import numpy as np
import matplotlib.pyplot as plt
import base64
import io

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# --- Azure OpenAI Client Initialization ---
def initialize_openai_client():
    """Initialize and return AzureOpenAI client with error handling"""
    try:
        # Check if all required config values are present
        if not all([config.CHAT_COMPLETIONS_PROJECT_ENDPOINT, config.CHAT_COMPLETIONS_SUBSCRIPTION_KEY, config.CHAT_COMPLETIONS_API_VERSION]):
             print("Warning: Azure OpenAI client not initialized. Missing one or more configuration values.")
             return None
        return AzureOpenAI(
            azure_endpoint=config.CHAT_COMPLETIONS_PROJECT_ENDPOINT,
            api_key=config.CHAT_COMPLETIONS_SUBSCRIPTION_KEY,
            api_version=config.CHAT_COMPLETIONS_API_VERSION
        )
    except Exception as e:
        print(f"Failed to initialize AzureOpenAI client: {str(e)}")
        return None

client = initialize_openai_client()

# --- Database Connection Handling ---
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

# --- Helper Decorator for Retries ---
def retry(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        raise
                    time.sleep(delay * retries)
        return wrapper
    return decorator


# --- Agent tools ---
@tool
@retry(max_retries=3)
def get_deals_data() -> dict:
    """
    Fetch deals data from Delta table with retry logic
    Returns:
        dict: {'columns': list, 'data': list of records}
    """
    try:
        df = read_data_from_delta()

        # Convert NaN to None for JSON serialization
        df = df.replace({np.nan: None})
        
        return {
            "columns": df.columns.tolist(),
            ## Increased to 100 for more data
            #"data": df.head(100).to_dict('records')
            "data": df.to_dict('records') 
        }
    except Exception as e:
        print(f"Error in get_deals_data: {str(e)}")
        return {"error": str(e)}


## Get data from databricks delta tables
def read_data_from_delta() -> pd.DataFrame:
    """
    Read data from Delta table with proper resource handling
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise ConnectionError("Failed to establish database connection")
            
        cursor = conn.cursor()
        cursor.execute(config.query)
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        return pd.DataFrame(data, columns=columns)
        
    finally:
        if conn:
            conn.close()


# --- Graph Generation Tools ---
@tool
def generate_bar_chart(labels: List[str], values: List[float], title: str) -> Dict[str, Any]:
    """Generate bar chart configuration"""
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Realized Value",
                "data": values,
                "backgroundColor": 'rgba(54, 162, 235, 0.7)',
                "borderColor": 'rgba(54, 162, 235, 1)',
                "borderWidth": 1
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {"display": True, "text": title}
            },
            "scales": {"y": {"beginAtZero": True}}
        }
    }


@tool
def generate_line_chart(labels: List[str], values: List[float], title: str) -> Dict[str, Any]:
    """Generate line chart configuration"""
    return {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Realized Value",
                "data": values,
                "fill": False,
                "borderColor": 'rgb(75, 192, 192)',
                "tension": 0.1
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {"display": True, "text": title}
            }
        }
    }

@tool
def generate_pie_chart(labels: List[str], values: List[float], title: str) -> Dict[str, Any]:
    """Generate pie chart configuration"""
    # Pie charts work best with positive values, so we filter for them
    positive_data = [(label, value) for label, value in zip(labels, values) if value > 0]
    if not positive_data:
        return {"error": "No positive data available for Pie Chart."}
    
    new_labels, new_values = zip(*positive_data)

    return {
        "type": "pie",
        "data": {
            "labels": new_labels,
            "datasets": [{
                "label": title,
                "data": new_values,
                "backgroundColor": [
                    'rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)', 'rgba(75, 192, 192, 0.7)',
                    'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)'
                ]
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {"display": True, "text": title}
            }
        }
    }

@tool
def generate_deals_chart(chart_type: str = "bar") -> Dict[str, Any]:
    """
    Generate chart from deals data
    Args:
        chart_type: Type of chart ('bar', 'line', 'pie')
    """
    deals_data = get_deals_data()
    if "error" in deals_data:
        return {"error": deals_data["error"]}
    
    df = pd.DataFrame(deals_data["data"])
    
    if df.empty:
        return {"error": "No deals data available"}

    # Ensure required columns exist
    if 'ltd_realized_value' not in df.columns or 'deal_num' not in df.columns:
        return {"error": "Required columns ('deal_num', 'ltd_realized_value') not found in data."}

    # Convert and clean data
    df['ltd_realized_value'] = pd.to_numeric(df['ltd_realized_value'], errors='coerce')
    df = df.dropna(subset=['ltd_realized_value'])
    
    if df.empty:
        return {"error": "No valid numeric data available for charting."}

    # Group by deal_num to aggregate results
    chart_data = df.groupby('deal_num')['ltd_realized_value'].sum().reset_index()

    # Prepare chart data
    labels = chart_data['deal_num'].astype(str).tolist()
    values = chart_data['ltd_realized_value'].tolist()
    title = "Deals Analysis: Realized Value"
    
    if chart_type == "bar":
        return generate_bar_chart(labels, values, title)
    elif chart_type == "line":
        return generate_line_chart(labels, values, title)
    elif chart_type == "pie":
        return generate_pie_chart(labels, values, title)
    else:
        return {"error": "Invalid chart type specified"}
    
    
# --- Text Analysis Tools ---
@tool
def get_insights_from_text(text_content: str, analysis_type: str = "summary") -> str:
    """
    Enhanced text analysis with configurable analysis types
    Args:
        text_content: Text to analyze
        analysis_type: Type of analysis ('summary', 'key_points', 'detailed')
    """
    if not text_content:
        return "Error: No text content provided"
    
    if not client:
        return "Error: AI client not initialized. Please check your configuration."

    try:
        system_messages = {
            "summary": "Provide a concise summary of the key points.",
            "key_points": "Extract the main bullet points.",
            "detailed": "Provide a comprehensive analysis with examples."
        }

        messages = [
            {"role": "system", "content": system_messages.get(analysis_type, system_messages["summary"])},
            {"role": "user", "content": text_content}
        ]

        response = client.chat.completions.create(
            model=config.CHAT_COMPLETIONS_MODEL_DEPLOYMENT,
            messages=messages,
            temperature=0.7,
            max_tokens=3000,
            top_p=0.95
        )

        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        return "Error: No content in response"
        
    except Exception as e:
        print(f"Error in get_insights_from_text: {str(e)}")
        return f"Analysis failed: {str(e)}"
