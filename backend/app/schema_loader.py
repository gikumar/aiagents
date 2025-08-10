# backend/app/schema_loader.py

import os
import json
import databricks.sql
from databricks.sql import OperationalError
from . import config
import logging

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

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "cache", "databricks_schema.json")

DATABRICKS_SERVER_HOSTNAME = config.DATABRICKS_SERVER_HOSTNAME
DATABRICKS_HTTP_PATH = config.DATABRICKS_HTTP_PATH
DATABRICKS_ACCESS_TOKEN = config.DATABRICKS_ACCESS_TOKEN

CATALOG = config.DATABRICKS_CATALOG
SCHEMA = config.DATABRICK_SCHEMA

def fetch_schema_from_databricks():
    try:
        logger.info(f"Fetching schema from databricks")
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

            logger.info(f"Schema successfully written to {SCHEMA_FILE}")

    except OperationalError as e:
        logger.info(f"Databricks connection failed: {e}")
    except Exception as e:
        logger.info(f"Unexpected error: {e}")

def fetch_table_columns():
    fetch_schema_from_databricks()
    with open(SCHEMA_FILE) as f:
        return json.load(f)