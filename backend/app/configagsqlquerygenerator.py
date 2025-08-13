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
###INSTRUCTIONS ARE IN SQL QUERY GENERATOR
"""