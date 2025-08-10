# backend/app/graph_service.py
import json
import re
import pandas as pd
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from databricks import sql
import traceback
import logging
from .config import (
    DATABRICKS_SERVER_HOSTNAME,
    DATABRICKS_ACCESS_TOKEN,
    DATABRICKS_HTTP_PATH
)
from .schema_utils import load_schema

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Create console handler with higher level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class GraphService:
    @staticmethod
    def infer_chart_type(prompt: str) -> str:
        logger.debug(f"Inferring chart type from prompt: {prompt[:100]}...")
        if "line" in prompt.lower():
            logger.debug("Chart type inferred as: line")
            return "line"
        elif "pie" in prompt.lower():
            logger.debug("Chart type inferred as: pie")
            return "pie"
        else: 
            logger.debug("Chart type inferred as: bar (default)")
            return "bar"

    @staticmethod
    def infer_top_n(prompt: str, default: int = 10) -> int:
        logger.debug(f"Checking for top N value in prompt: {prompt[:100]}...")
        match = re.search(r"top\s+(\d+)", prompt.lower())
        if match:
            top_n = int(match.group(1))
            logger.debug(f"Found top_n value: {top_n}")
            return top_n
        logger.debug(f"Using default top_n value: {default}")
        return default

    @staticmethod
    def generate_from_query_results(query_results: dict, prompt: str) -> dict:
        logger.info("Starting graph generation from query results")
        if not query_results.get('data'):
            logger.error("No data available in query results for graph generation")
            return {
                "status": "error",
                "message": "No data available for graph",
                "query_results": query_results
            }
        
        try:
            logger.debug("Creating DataFrame from query results")
            df = pd.DataFrame(query_results['data'])
            logger.debug(f"DataFrame created with shape: {df.shape}")
            
            if len(df.columns) < 2:
                logger.error(f"Insufficient columns for graph. Available: {df.columns.tolist()}")
                return {
                    "status": "error",
                    "message": "Need at least 2 columns for graph",
                    "available_columns": df.columns.tolist()
                }

            label_col = df.columns[0]
            value_col = df.columns[1]
            logger.debug(f"Using columns - Labels: {label_col}, Values: {value_col}")
            
            chart_type = GraphService.infer_chart_type(prompt)
            top_n = GraphService.infer_top_n(prompt)
            
            logger.debug(f"Sorting by {value_col} and taking top {top_n}")
            df = df.sort_values(by=value_col, ascending=False)
            if top_n > 0:
                df = df.head(top_n)
            
            labels = df[label_col].astype(str).tolist()
            values = pd.to_numeric(df[value_col], errors='coerce').fillna(0).tolist()
            logger.debug(f"Generated {len(labels)} labels and {len(values)} values")
            
            dataset_label = f"Top {len(values)} by Realized Value"
            if value_col != "realized_value":
                dataset_label = f"Top {len(values)} by {value_col.replace('_', ' ').title()}"
            
            logger.info("Successfully generated graph data from query results")
            return {
                "status": "success",
                "graph": {
                    "type": chart_type,
                    "labels": labels,
                    "values": values,
                    "dataset_label": dataset_label,
                    "title": f"Top {len(values)} Deals by Realized Value"
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating graph from query results: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": f"Graph generation failed: {str(e)}",
                "query_results": query_results,
                "traceback": traceback.format_exc()
            }

    def execute_sql_query(sql_query: str) -> dict:
        logger.info(f"Executing SQL query: {sql_query[:100]}...")
        try:
            with sql.connect(
                server_hostname=DATABRICKS_SERVER_HOSTNAME,
                http_path=DATABRICKS_HTTP_PATH,
                access_token=DATABRICKS_ACCESS_TOKEN
            ) as conn:
                with conn.cursor() as cursor:
                    logger.debug("Connected to Databricks, executing query")
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
                    
                    logger.info(f"Query executed successfully. Returned {len(data)} rows")
                    return {
                        "status": "success",
                        "columns": columns,
                        "data": data,
                        "query": sql_query,
                        "row_count": len(data)
                    }
        except Exception as e:
            logger.error(f"SQL query execution failed: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": str(e),
                "query": sql_query,
                "error_type": type(e).__name__
            }


    @staticmethod  
    def _try_extract_embedded_data(prompt: str) -> Optional[dict]:
      """Helper to extract embedded data from prompt if present"""
      if "The data is as follows:" not in prompt.lower():
            return None
            
      try:
            deal_nums = re.search(r"Deal Numbers: (\[[^\]]+\])", prompt)
            pnl_values = re.search(r"Realized PnL Values: (\[[^\]]+\])", prompt)
            
            if deal_nums and pnl_values:
                  labels = json.loads(deal_nums.group(1))
                  values = json.loads(pnl_values.group(1))
                  values = [v/1e9 for v in values]  # Convert to billions
                  
                  return {
                  "status": "success",
                  "graph": {
                        "type": "bar",
                        "labels": labels,
                        "values": values,
                        "dataset_label": "Realized PnL (in billions)",
                        "title": "Top Deals by Realized PnL"
                  }
                  }
      except Exception as e:
            logger.warning(f"Failed to parse embedded data: {str(e)}")
      return None
      
    @staticmethod
    def generate_from_prompt(prompt: str) -> dict:
      logger.info("Starting graph generation from prompt")
      try:
            logger.debug(f"Original prompt: {prompt[:200]}...")
            
            # First try to extract embedded data if present
            embedded_data_result = GraphService._try_extract_embedded_data(prompt)
            if embedded_data_result:
                  return embedded_data_result
                  
            # If no embedded data, generate SQL and execute
            from .agsqlquerygenerator import AGSQLQueryGenerator
            logger.info("Generating SQL from prompt")
            
            sql_generator = AGSQLQueryGenerator()
            enhanced_prompt = (
                  "Generate a Databricks SQL query to fetch data for visualization. "
                  "The query should return exactly two columns: "
                  "1. First column: labels/categories (e.g., deal numbers, dates)"
                  "2. Second column: numeric values to visualize\n\n"
                  f"Original request: {prompt}"
            )
            
            sql_query = sql_generator.invoke(enhanced_prompt)
            logger.debug(f"Generated SQL: {sql_query}")
            
            if not sql_query.lstrip().upper().startswith(("SELECT", "WITH")):
                  raise ValueError("Generated query is not valid SQL")
                  
            # Execute and process results
            logger.info("Executing SQL query")
            query_results = GraphService.execute_sql_query(sql_query)
            
            if query_results.get("status") != "success":
                  logger.error("SQL execution failed")
                  return {
                  "status": "error",
                  "message": "SQL execution failed",
                  "details": query_results,
                  "available_columns": query_results.get("columns", [])
                  }

            return GraphService.generate_from_query_results(query_results, prompt)
            
      except Exception as e:
            logger.error(f"Critical error in generate_from_prompt: {str(e)}")
            return {
                  "status": "error",
                  "message": f"Failed to generate graph: {str(e)}",
                  "details": traceback.format_exc()
            }
      
    
  
    
    def extract_data_from_error_prompt(prompt: str) -> dict:
            """Fallback to extract data directly from prompt when SQL fails"""
            deals = []
            values = []
    
            # Extract deal numbers and values from prompt text
            for line in prompt.split('\n'):
                  if "Deal" in line and "$" in line:
                        parts = line.split(':')
                        if len(parts) == 2:
                              deal_num = parts[0].strip().split()[-1]
                              value_str = parts[1].strip().replace('$', '').replace(',', '')
                              try:
                                    deals.append(deal_num)
                                    values.append(float(value_str))
                              except ValueError:
                                    continue
    
            if deals and values:
                  return {
                        "status": "success",
                        "graph": {
                        "type": "bar",
                        "labels": deals,
                        "values": values,
                        "dataset_label": "LTD Realized PnL",
                        "title": "Top Deals by LTD Realized PnL"
                        }
                  }
            raise ValueError("Could not extract data from prompt")