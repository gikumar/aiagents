# backend/app/tools.py
import json
import re
from datetime import datetime, date
from typing import Dict, List, Optional
import pandas as pd
from databricks import sql
from .config import (
    DATABRICKS_SERVER_HOSTNAME,
    DATABRICKS_ACCESS_TOKEN,
    DATABRICKS_HTTP_PATH
)
import traceback


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def execute_databricks_query(sql_query: str) -> Dict:
    """
    Enhanced Databricks query execution with:
    1. Automatic error recovery
    2. Schema validation
    3. Self-healing queries
    """
    # First validate the query
    validation = validate_databricks_query(sql_query)
    if not validation["is_valid"]:
        return {
            "status": "error",
            "message": f"Query validation failed: {validation['message']}",
            "query": sql_query,
            "suggested_fixes": validation.get("suggestions", [])
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
        # Handle column resolution errors with automatic recovery
        if "UNRESOLVED_COLUMN" in str(e):
            return handle_column_error(e, sql_query)
        # Handle syntax errors for DISTINCT and other keywords
        elif "PARSE_SYNTAX_ERROR" in str(e):
            return handle_syntax_error(e, sql_query)
        return {
            "status": "error",
            "message": str(e),
            "query": sql_query,
            "error_type": type(e).__name__
        }

def handle_column_error(error: Exception, query: str) -> Dict:
    """
    Automatically handle column resolution errors by:
    1. Extracting suggested columns from error
    2. Fetching table schema if needed
    3. Providing corrected query suggestions
    """
    error_msg = str(error)
    table_match = re.search(r"FROM\s+([^\s,;]+)", query, re.IGNORECASE)
    table = table_match.group(1) if table_match else "unknown_table"
    
    # Extract suggested columns from error
    suggestions = []
    if "Did you mean one of the following?" in error_msg:
        suggestions = re.findall(r"`([^`]+)`", error_msg.split("following?")[1])
    
    # Get full schema if we have table name
    schema_info = {}
    if table != "unknown_table":
        schema_info = describe_table(table)
    
    # Try to find similar columns
    bad_column = re.search(r"name `([^`]+)`", error_msg)
    if bad_column:
        bad_col = bad_column.group(1)
        similar_cols = find_similar_columns(bad_col, schema_info.get("data", []))
        suggestions.extend(similar_cols)
    
    # Build corrected query if possible
    corrected_query = None
    if bad_column and suggestions:
        corrected_query = query.replace(
            bad_col, 
            suggestions[0]  # Use first suggestion
        )
    
    return {
        "status": "error",
        "message": error_msg,
        "query": query,
        "error_type": "ColumnResolutionError",
        "suggested_columns": suggestions,
        "corrected_query": corrected_query,
        "schema_info": schema_info,
        "recommendation": "Try using one of the suggested columns"
    }

def handle_syntax_error(error: Exception, query: str) -> Dict:
    """Enhanced syntax error handling with DISTINCT fixes"""
    error_msg = str(error)
    
    # Handle DISTINCT syntax issues
    if "DISTINCT" in query.upper() and ("PARSE_SYNTAX_ERROR" in error_msg or "UNEXPECTED_TOKEN" in error_msg):
        # Fix 1: Remove parentheses
        fixed_query = re.sub(
            r"DISTINCT\s*\(\s*([^)]+)\s*\)",
            r"DISTINCT \1",
            query,
            flags=re.IGNORECASE
        )
        
        # Fix 2: Ensure proper column separation
        fixed_query = re.sub(
            r"DISTINCT\s*([^,\s]+)\s*,\s*",
            r"DISTINCT \1,",
            fixed_query,
            flags=re.IGNORECASE
        )
        
        return {
            "status": "error",
            "message": error_msg,
            "query": query,
            "error_type": "SyntaxError",
            "corrected_queries": [
                fixed_query,
                # Alternative suggestion without DISTINCT
                query.replace("DISTINCT", "").replace("  ", " ")
            ],
            "recommendation": "Try removing parentheses from DISTINCT clause"
        }
    
    return {
        "status": "error",
        "message": error_msg,
        "query": query,
        "error_type": "SyntaxError"
    }


def describe_table(table_name: str) -> Dict:
    """Fetch schema information for a table"""
    try:
        with sql.connect(
            server_hostname=DATABRICKS_SERVER_HOSTNAME,
            http_path=DATABRICKS_HTTP_PATH,
            access_token=DATABRICKS_ACCESS_TOKEN
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"DESCRIBE TABLE {table_name}")
                columns = [desc[0] for desc in cursor.description]
                data = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return {
                    "status": "success",
                    "columns": columns,
                    "data": data,
                    "table": table_name
                }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "table": table_name
        }

def find_similar_columns(target: str, schema_data: List[Dict]) -> List[str]:
    """
    Find columns similar to target in schema data
    """
    target_lower = target.lower()
    similar = []
    for col_info in schema_data:
        col_name = col_info.get("col_name", "")
        if target_lower in col_name.lower() or col_name.lower() in target_lower:
            similar.append(col_name)
    return similar


# Updated tools.py with proper DISTINCT handling
def validate_databricks_query(query: str) -> Dict:
    """Validate SQL query syntax with enhanced DISTINCT handling"""
    # Standard validation checks
    if re.search(r"\b(DROP|DELETE|UPDATE|INSERT)\b", query, re.IGNORECASE):
        return {
            "is_valid": False,
            "message": "Write operations are not allowed",
            "suggestions": ["Use SELECT queries only"]
        }
    
    # Check for valid table references
    tables = re.findall(r"FROM\s+([^\s,;]+)", query, re.IGNORECASE)
    if not tables:
        return {
            "is_valid": False,
            "message": "No tables referenced in query",
            "suggestions": ["Add a FROM clause with a valid table name"]
        }

    # Enhanced DISTINCT validation
    if "DISTINCT" in query.upper():
        distinct_pattern = re.compile(
            r"SELECT\s+DISTINCT\s+(?:\(\s*([^)]+)\s*\)|([^,\s]+))", 
            re.IGNORECASE
        )
        match = distinct_pattern.search(query)
        
        if not match:
            return {
                "is_valid": False,
                "message": "Invalid DISTINCT syntax",
                "suggestions": [
                    "Remove parentheses: DISTINCT trader",
                    "For multiple columns: DISTINCT col1, col2"
                ]
            }
        
        # Extract column name whether in parentheses or not
        column = match.group(1) or match.group(2)
        if not column.strip():
            return {
                "is_valid": False,
                "message": "DISTINCT with empty column list",
                "suggestions": ["Specify columns after DISTINCT"]
            }

    return {
        "is_valid": True,
        "referenced_tables": tables
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
    if not query_results.get('data'):
        return {
            "status": "error",
            "message": "No data available for graph",
            "query_results": query_results
        }

    try:
        # 1. Create DataFrame
        df = pd.DataFrame(query_results['data'])
        print("\n=== DEBUG: DataFrame ===")
        print(df)
        
        # 2. Validate columns
        if len(df.columns) < 2:
            return {
                "status": "error",
                "message": "Need at least 2 columns for graph (labels and values)",
                "available_columns": df.columns.tolist()
            }

        # 3. Dynamically determine columns
        # First column is always labels (deal identifiers)
        label_col = df.columns[0]
        
        # Second column is always values (realized value)
        value_col = df.columns[1]
        
        # 4. Process data
        chart_type = infer_chart_type(prompt)
        top_n = infer_top_n(prompt)
        
        # Sort and limit
        df = df.sort_values(by=value_col, ascending=False)
        if top_n > 0:
            df = df.head(top_n)
        
        # Get labels and values
        labels = df[label_col].astype(str).tolist()
        values = pd.to_numeric(df[value_col], errors='coerce').fillna(0).tolist()
        
        print("\n=== DEBUG: Processed Graph Data ===")
        print(f"Labels: {labels}")
        print(f"Values: {values}")
        
        # Create a readable label for the dataset
        dataset_label = f"Top {len(values)} by Realized Value"
        if value_col != "realized_value":
            # Try to make the label more descriptive
            dataset_label = f"Top {len(values)} by {value_col.replace('_', ' ').title()}"
        
        return {
            "status": "success",
            "graphData": {
                "type": chart_type,
                "labels": labels,
                "values": values,
                "dataset_label": dataset_label,
                "title": f"Top {len(values)} Deals by Realized Value"
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Graph generation failed: {str(e)}",
            "query_results": query_results,
            "traceback": traceback.format_exc()
        }
    


# Graph utility functions (from graph_utils.py)
# tools.py
def infer_y_axis_column(prompt: str, df: pd.DataFrame) -> str:
    prompt_lower = prompt.lower()
    
    # 1. Check for exact column matches first
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ["realized_pnl", "realized_value", "pnl"]):
            if col_lower in prompt_lower:
                return col
    
    # 2. Try common PnL variations using schema knowledge
    pnl_variations = [
        'ltd_realized_value', 'ytd_realized_value', 'mtd_realized_value',
        'dtd_realized_value', 'realized_value_eur', 'trade_price'
    ]
    for variation in pnl_variations:
        if variation in df.columns:
            return variation
    
    # 3. Fallback to first numeric column
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            return col
    
    # 4. Final fallback
    return df.columns[1] if len(df.columns) > 1 else df.columns[0]


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
            if str(trader).lower() in prompt_lower:
                df = df[df['trader'].str.lower() == trader.lower()]
                break

    # Filter by counterparty
    if 'counterparty' in df.columns:
        for cp in df['counterparty'].dropna().unique():
            if str(cp.lower()) in prompt_lower:
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


def generate_graph_from_prompt(prompt: str) -> Dict:
    """
    End-to-end pipeline for generating graph data from natural language prompts.
    
    This function serves as the primary interface between natural language requests
    and data graphs by orchestrating three key stages:
    1. SQL Generation: Converts natural language prompts into executable SQL queries
    2. Data Retrieval: Executes queries against the Databricks data warehouse
    3. graph Preparation: Transforms query results into chart-ready data
    
    The pipeline:
    a. Accepts user prompts like "Show top 5 traders by PnL as bar chart"
    b. Generates SQL using specialized NLP-to-SQL agent
    c. Executes SQL against Databricks Unity Catalog
    d. Processes results into graph specifications (chart type, axes, data)
    
    Returns a standardized response containing either:
    - Successful graph data payload (status: "success"), or
    - Detailed error information (status: "error")
    
    Response Structure (success):
    {
        "status": "success",
        "response": "Here's the requested graph:",
        "graph_data": {
            "chart_type": "bar"|"line"|"pie",
            "x_axis": "trader",
            "y_axis": "total_realized_pnl",
            "data": [...]  // Processed dataset
        }
    }
    
    Response Structure (error):
    {
        "status": "error",
        "message": "Descriptive error message",
        "details": "Technical details/traceback"
    }
    
    This function is designed to be registered directly with AI agents as a tool
    for natural language-driven data graph.
    
    Args:
        prompt: Natural language request for data graph
        
    Returns:
        dict: Standardized response containing either graph data or error information
    """
    try:
        print("\n=== DEBUG: Starting graph generation ===")
        print(f"Original prompt: {prompt}")
        
        from .agsqlquerygenerator import AGSQLQueryGenerator
        # Step 1: Generate SQL from prompt
        sql_generator = AGSQLQueryGenerator()
        sql_query_string = sql_generator.invoke(prompt)
        sql_response = {
            "status": "success",
            "sql_query": sql_query_string
        }
        
        print(f"\n=== DEBUG: Generated SQL ===\n{sql_query_string}\n")
        
        # Step 2: Run the SQL query
        query_results = execute_databricks_query(sql_response["sql_query"])
        print(f"\n=== DEBUG: Query Results ===\n{json.dumps(query_results, indent=2)}\n")
        
        if query_results.get("status") != "success":
            print("=== DEBUG: SQL Execution Failed ===")
            return {
                "status": "error",
                "message": "SQL execution failed",
                "details": query_results
            }

        # Step 3: Generate the graph data
        graph_result = generate_graph_data(query_results, prompt)
        print("\n=== DEBUG: Graph Result ===")
        print(json.dumps(graph_result, indent=2))
        
        # Return structured response expected by frontend
        if graph_result.get("status") == "success":
            graph_data = graph_result["graphData"]
            print("\n=== DEBUG: Final Graph Data ===")
            print(json.dumps(graph_data, indent=2))
            
            # Check for empty values
            if not graph_data["values"] or len(graph_data["values"]) == 0:
                print("=== DEBUG: Empty Values Detected ===")
                return {
                    "status": "error",
                    "message": "Graph data contains empty values",
                    "details": {
                        "inferred_y_axis": graph_data["dataset_label"].split()[-1],
                        "available_columns": query_results["columns"]
                    }
                }
                
            return {
                "status": "success",
                "response": "Here's the requested graph:",
                "graph_data": {
                    "type": graph_data["type"],
                    "labels": graph_data["labels"],
                    "values": graph_data["values"],
                    "dataset_label": graph_data["dataset_label"],
                    "title": graph_data["title"]
                }
            }
        else:
            return graph_result
            
    except Exception as e:
        print(f"\n=== DEBUG: Exception ===\n{traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Failed to generate graph: {str(e)}",
            "details": traceback.format_exc()
        }

# Maintain empty user_functions dict as expected by agentfactory.py
user_functions = {}