#Sharing next file just keep it and do not analyze until i confirm I have shared all the files
# backend/app/schema_routes.py

from fastapi import APIRouter, HTTPException
from .schema_utils import load_schema

router = APIRouter()

@router.get("/columns/{table_name}")
def get_table_columns(table_name: str):
    schema_data = load_schema()
    table = table_name.lower()
    if table not in schema_data:
        raise HTTPException(status_code=404, detail="Table not found")
    return {"columns": schema_data[table]}


@router.post("/columns/refresh")
def refresh_columns():
    from .schema_loader import fetch_table_columns
    return fetch_table_columns()