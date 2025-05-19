# filepath: backend/services/database/__init__.py
"""
Database package for the application.

This package provides database access and querying functionality
for various database backends.
"""

from .mongo import query_mongo
from .postgres import query_postgres

__all__ = [
    'query_mongo',
    'query_postgres',
]
