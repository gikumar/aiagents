# backend/app/schema_routes.py

from fastapi import APIRouter, HTTPException
from .schema_utils import load_schema
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

router = APIRouter()

@router.get("/columns/{table_name}")
def get_table_columns(table_name: str):
    logger.info(f"Schema Routes: getting tables columns name")
    schema_data = load_schema()
    table = table_name.lower()
    if table not in schema_data:
        logger.info(f"Schema Routes: table not found")    
        raise HTTPException(status_code=404, detail="Table not found")
    return {"columns": schema_data[table]}


@router.post("/columns/refresh")
def refresh_columns():
    logger.info(f"Schema Routes: refreshing columns on startup")
    from .schema_loader import fetch_table_columns
    return fetch_table_columns()