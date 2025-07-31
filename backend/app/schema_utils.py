#Sharing next file just keep it and do not analyze until i confirm I have shared all the files
# backend/app/schema_utils.py

import os
import json
from pathlib import Path
from .config import DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN
from databricks import sql

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "cache", "databricks_schema.json")

def load_schema() -> dict:
    schema_file = Path(__file__).parent / "cache/databricks_schema.json"
    print(f"[DEBUG] Loading schema from: {schema_file}")
    with open(schema_file) as f:
        schema = json.load(f)
    print(f"[DEBUG] Loaded {len(schema)} tables from schema")
    return schema

def fetch_and_save_schema():
    conn = sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_ACCESS_TOKEN,
        _verify_ssl=False,
        timeout=60
    )
    try:
        schema = {}
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES IN trade_catalog.trade_schema")
            tables = [row[1] for row in cursor.fetchall()]  # second column is table name

            for table in tables:
                cursor.execute(f"DESCRIBE TABLE trade_catalog.trade_schema.{table}")
                columns = [row[0] for row in cursor.fetchall()]
                schema[table] = columns

        os.makedirs(os.path.dirname(SCHEMA_FILE), exist_ok=True)
        with open(SCHEMA_FILE, "w") as f:
            json.dump(schema, f, indent=2)
        print("Schema saved to databricks_schema.json")

    finally:
        conn.close()