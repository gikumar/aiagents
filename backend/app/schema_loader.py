#Sharing next file just keep it and do not analyze until i confirm I have shared all the files
# backend/app/schema_loader.py

import os
import json
import databricks.sql
from databricks.sql import OperationalError
from . import config

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "cache", "databricks_schema.json")

# ✅ FIX: Don't add commas!
DATABRICKS_SERVER_HOSTNAME = config.DATABRICKS_SERVER_HOSTNAME
DATABRICKS_HTTP_PATH = config.DATABRICKS_HTTP_PATH
DATABRICKS_ACCESS_TOKEN = config.DATABRICKS_ACCESS_TOKEN

CATALOG = config.DATABRICKS_CATALOG
SCHEMA = config.DATABRICK_SCHEMA

def fetch_schema_from_databricks():
    try:
        with databricks.sql.connect(
            server_hostname=DATABRICKS_SERVER_HOSTNAME,
            http_path=DATABRICKS_HTTP_PATH,
            access_token=DATABRICKS_ACCESS_TOKEN
        ) as conn:
            cursor = conn.cursor()

            # Step 1: Get all tables in the schema
            cursor.execute(f"SHOW TABLES IN {CATALOG}.{SCHEMA}")
            tables = cursor.fetchall()

            schema_dict = {}

            # Step 2: For each table, get columns
            for table_row in tables:
                table_name = table_row[1]  # Second column is table name
                full_table_name = f"{CATALOG}.{SCHEMA}.{table_name}"

                cursor.execute(f"DESCRIBE TABLE {full_table_name}")
                column_rows = cursor.fetchall()
                column_names = [row[0] for row in column_rows if row[0] and not row[0].startswith("#")]

                schema_dict[table_name.lower()] = column_names

            # Step 3: Write to JSON file
            with open(SCHEMA_FILE, "w") as f:
                json.dump(schema_dict, f, indent=2)

            print(f"✅ Schema successfully written to {SCHEMA_FILE}")

    except OperationalError as e:
        print(f"❌ Databricks connection failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def fetch_table_columns():
    fetch_schema_from_databricks()
    with open(SCHEMA_FILE) as f:
        return json.load(f)