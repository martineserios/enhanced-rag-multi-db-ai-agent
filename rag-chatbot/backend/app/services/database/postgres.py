# filepath: backend/services/database/postgres.py
"""
PostgreSQL database service.

This module provides functionality for connecting to and querying a PostgreSQL
database, with support for natural language queries using the LLM.
"""
import os
import json
import re
from typing import Dict, List, Any, Optional, Union
import asyncio
from datetime import datetime, date, time, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import pandas as pd

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    DatabaseError, DatabaseConnectionError, DatabaseQueryError
)
from app.config import Settings


logger = get_logger(__name__)

# Global engine reference
_engine = None
_async_session = None


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for PostgreSQL data types."""
    
    def default(self, obj):
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return str(obj)
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        return super().default(obj)


async def init_postgres(settings: Settings):
    """
    Initialize the PostgreSQL database connection.
    
    Args:
        settings: Application configuration settings
        
    Returns:
        SQLAlchemy async engine
        
    Raises:
        DatabaseConnectionError: If the connection fails
    """
    global _engine, _async_session
    
    try:
        # Convert the synchronous URI to async
        sync_uri = settings.postgres_uri
        if sync_uri.startswith("postgresql://"):
            async_uri = sync_uri.replace("postgresql://", "postgresql+asyncpg://")
        else:
            async_uri = sync_uri
        
        # Create the async engine
        _engine = create_async_engine(
            async_uri,
            echo=settings.debug,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800  # Recycle connections after 30 minutes
        )
        
        # Create session factory
        _async_session = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Test the connection
        async with _engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info(f"PostgreSQL initialized successfully")
        return _engine
        
    except Exception as e:
        logger.exception("Failed to initialize PostgreSQL connection")
        raise DatabaseConnectionError(f"PostgreSQL connection failed: {str(e)}")


async def get_session():
    """
    Get a database session.
    
    Yields:
        AsyncSession: SQLAlchemy async session
        
    Raises:
        DatabaseError: If PostgreSQL is not initialized
    """
    global _async_session
    if _async_session is None:
        raise DatabaseError("PostgreSQL not initialized. Call init_postgres first.")
    
    async with _async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise


@log_execution_time(logger)
async def execute_sql(query: str) -> List[Dict[str, Any]]:
    """
    Execute a SQL query and return the results.
    
    Args:
        query: SQL query to execute
        
    Returns:
        List of dictionaries with query results
        
    Raises:
        DatabaseQueryError: If the query fails
    """
    global _engine
    if _engine is None:
        raise DatabaseError("PostgreSQL not initialized. Call init_postgres first.")
    
    try:
        async with _engine.connect() as conn:
            # Execute the query
            result = await conn.execute(text(query))
            
            # Get column names and rows
            columns = result.keys()
            rows = result.fetchall()
            
            # Convert rows to dictionaries
            results = []
            for row in rows:
                # Convert row to dictionary
                row_dict = dict(zip(columns, row))
                results.append(row_dict)
            
            logger.debug(
                f"SQL query executed successfully",
                extra={
                    "query": query[:1000] + "..." if len(query) > 1000 else query,
                    "row_count": len(results)
                }
            )
            
            return results
    
    except Exception as e:
        logger.exception(f"Error executing SQL query: {query[:200]}...")
        raise DatabaseQueryError(f"SQL query failed: {str(e)}")


async def _get_table_schema() -> Dict[str, List[Dict[str, str]]]:
    """
    Get the schema of all tables in the database.
    
    Returns:
        Dictionary mapping table names to their columns and types
        
    Raises:
        DatabaseQueryError: If retrieving the schema fails
    """
    try:
        # Query for tables
        tables_query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """
        tables = await execute_sql(tables_query)
        
        schema = {}
        
        # For each table, get its columns
        for table_info in tables:
            table_name = table_info["table_name"]
            
            columns_query = f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = '{table_name}'
            ORDER BY ordinal_position
            """
            
            columns = await execute_sql(columns_query)
            schema[table_name] = columns
        
        return schema
        
    except Exception as e:
        logger.exception("Error retrieving database schema")
        raise DatabaseQueryError(f"Failed to retrieve database schema: {str(e)}")


@log_execution_time(logger)
async def query_postgres(question: str, settings: Settings) -> str:
    """
    Generate SQL from a natural language question and execute it.
    
    In a production implementation, this function would:
    1. Use an LLM to generate SQL from the natural language question
    2. Validate the SQL for safety
    3. Execute the SQL and format the results
    
    For simplicity, we use a predefined mapping here.
    
    Args:
        question: Natural language question
        settings: Application settings
        
    Returns:
        Formatted results as a JSON string
        
    Raises:
        DatabaseQueryError: If the query generation or execution fails
    """
    try:
        # For demo purposes, we'll use a predefined mapping
        # In a real implementation, use an LLM to generate SQL
        
        # Simple predefined queries
        predefined_queries = {
            "product": "SELECT * FROM products LIMIT 10",
            "products": "SELECT * FROM products LIMIT 10",
            "customer": "SELECT * FROM customers LIMIT 10",
            "customers": "SELECT * FROM customers LIMIT 10",
            "order": "SELECT * FROM orders LIMIT 10",
            "orders": "SELECT * FROM orders LIMIT 10",
            "sales": "SELECT SUM(price * quantity) as total_sales FROM orders",
            "total sales": "SELECT SUM(price * quantity) as total_sales FROM orders",
            "popular": "SELECT product_id, COUNT(*) as order_count FROM orders GROUP BY product_id ORDER BY order_count DESC LIMIT 5",
            "popular products": "SELECT p.name, COUNT(*) as order_count FROM orders o JOIN products p ON o.product_id = p.product_id GROUP BY p.product_id, p.name ORDER BY order_count DESC LIMIT 5",
            "revenue": "SELECT DATE_TRUNC('month', order_date) as month, SUM(price * quantity) as revenue FROM orders GROUP BY month ORDER BY month",
            "monthly revenue": "SELECT DATE_TRUNC('month', order_date) as month, SUM(price * quantity) as revenue FROM orders GROUP BY month ORDER BY month",
        }
        
        # More complex pattern matching
        # NOTE: In a production implementation, use an LLM for this
        question_lower = question.lower()
        query = None
        
        # Check for exact matches first
        for key, sql in predefined_queries.items():
            if key in question_lower:
                query = sql
                break
        
        # If no match, try more complex pattern matching
        if query is None:
            # Products by category
            category_match = re.search(r"products\s+in\s+(\w+)\s+category", question_lower)
            if category_match:
                category = category_match.group(1)
                query = f"SELECT * FROM products WHERE category ILIKE '%{category}%' LIMIT 10"
            
            # Orders by customer
            customer_match = re.search(r"orders\s+(?:from|by)\s+customer\s+(\w+)", question_lower)
            if customer_match and not query:
                customer = customer_match.group(1)
                query = f"""
                SELECT o.* FROM orders o
                JOIN customers c ON o.customer_id = c.customer_id
                WHERE c.name ILIKE '%{customer}%' OR c.email ILIKE '%{customer}%'
                LIMIT 10
                """
            
            # Products above price
            price_match = re.search(r"products\s+(?:over|above)\s+\$?(\d+)", question_lower)
            if price_match and not query:
                price = price_match.group(1)
                query = f"SELECT * FROM products WHERE price > {price} ORDER BY price LIMIT 10"
        
        # If still no match, use a default query
        if query is None:
            # Get database schema to provide context
            schema = await _get_table_schema()
            
            # Format schema information
            schema_info = []
            for table, columns in schema.items():
                cols = [f"{col['column_name']} ({col['data_type']})" for col in columns]
                schema_info.append(f"Table {table}: {', '.join(cols)}")
            
            # Return schema information instead
            return json.dumps({
                "info": "No specific SQL query could be generated for your question. Here is the database schema for reference:",
                "schema": schema_info
            }, cls=JSONEncoder, indent=2)
        
        # Execute the query
        results = await execute_sql(query)
        
        # Format the results
        if len(results) == 0:
            return json.dumps({
                "query": query,
                "results": "No results found for this query."
            }, cls=JSONEncoder, indent=2)
        
        # If it's a single value result (e.g., COUNT, SUM)
        if len(results) == 1 and len(results[0]) == 1:
            key = list(results[0].keys())[0]
            value = results[0][key]
            return json.dumps({
                "query": query,
                "result": {key: value}
            }, cls=JSONEncoder, indent=2)
        
        # For larger result sets, limit the output
        if len(results) > 20:
            display_results = results[:20]
            has_more = True
        else:
            display_results = results
            has_more = False
        
        response = {
            "query": query,
            "results": display_results,
            "row_count": len(results),
            "has_more": has_more
        }
        
        return json.dumps(response, cls=JSONEncoder, indent=2)
        
    except Exception as e:
        logger.exception(f"Error in query_postgres: {str(e)}")
        return json.dumps({
            "error": f"Failed to query the database: {str(e)}",
            "question": question
        }, indent=2)