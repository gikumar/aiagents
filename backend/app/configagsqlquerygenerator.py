#/backedn/app/configagsqlquerygenerator.py

from dotenv import load_dotenv
import os
load_dotenv()

# ----- CONFIGURATION -----
# Azure "EnC-Intl-Engg-Subs" Subscription 
DATABRICKS_SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
DATABRICKS_ACCESS_TOKEN = os.getenv("DATABRICKS_ACCESS_TOKEN")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")

orchestrator_agent_name= "AgentsOrchestrator"
sql_query_generator_agent_name= "SQLQueryGenerator"


sql_query_generator_instruction = """You are an expert SQL generator specialized in Databricks Unity Catalog Delta Tables. Your task is to understand the natural language prompts and generate accurate, executable SQL queries."""

"""
###COMMENTED OUT AS INSTRUCTIONS ARE THERE IN SQL QUERY GENERATOR

IMPROTANT RULE TO CONSIDER CAREFULLY:
1. You must use fully-qualified table names only (e.g., trade_catalog.trade_schema.entity_trade_header)
2. Available tables and columns come from databricks_schema.json.
For example if you generate a query "Select Coun(deal_num) from trade_catalog.trade_schema.entity_trade_header"
You must check that the table name used in query "entity_trade_header" is macthing with some table name in databricks_schema.json.
Similiarly You must check if deal_num is available in entity_trade_header table columns by reffering to databricks_schema.json
using only the schema provided from the 'databricks_schema.json'.
3. Do not invent table or column names.
4. Add LIMIT 50 by default unless otherwise instructed
5. Return ONLY the raw SQL query (no markdown, no explanation, no comments)
6. Dynamically read the table names from databricks_schema.json
7. Output Requirements:
   - Ensure queries start with `SELECT`.
   - Use `LIMIT` if the result set might be large.
   - Include `ORDER BY` if prompt refers to top values.
   - Avoid using `*`. Explicitly name all selected columns.
8. DO NOT Output partial SQL or invalid syntax
9. When user asks about data volumes, counts, tables, trends, or records, ALWAYS call `get_deals_aggrgated_data`.
"""