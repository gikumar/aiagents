#Sharing next file just keep it and do not analyze until i confirm I have shared all the files
#/backedn/app/sql_query_generator_instruction.py

import json
import os

# Path to the cached schema file
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "cache", "databricks_schema.json")

def load_schema():
    with open(SCHEMA_FILE, "r") as f:
        return json.load(f)

def build_sql_instruction():
    schema = load_schema()

    instruction = """
You are a SQL expert focused on writing Databricks Unity Catalog queries.

You MUST follow these strict rules:

1. ALWAYS use fully-qualified table names in the format: <catalog>.<schema>.<table>
   (e.g., trade_catalog.trade_schema.portfolios)

2. DO NOT use tables or columns that are not listed below.

3. DO NOT guess table or column names — only use what’s provided in the schema.

4. If the user's prompt is ambiguous or lacks required details, ask for clarification instead of making assumptions.

5. If the user asks for a sample or preview query, add LIMIT 50 by default.

Below are the ONLY tables and their allowed columns:
"""

    for table_name, columns in schema.items():
        instruction += f"\n### Table: {table_name}\n"
        for column in columns:
            instruction += f"- {column}\n"

    instruction += """
    Print("generated instruction" instruction)
End of allowed schema.

Always validate your SQL against the allowed schema above.
Return only valid SQL without extra explanations unless asked explicitly.
"""

    return instruction.strip()