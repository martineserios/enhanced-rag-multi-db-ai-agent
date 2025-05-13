# filepath: backend/services/database/neo4j.py
"""
Neo4j database service for the backend.

This module provides utilities for connecting to and querying
the Neo4j graph database.
"""
from typing import Dict, List, Any, Optional, Union
import json
import logging
import asyncio

from neo4j import AsyncGraphDatabase, Record, Transaction
from neo4j.exceptions import Neo4jError

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    DatabaseError, DatabaseConnectionError, DatabaseQueryError
)
from app.config import Settings


logger = get_logger(__name__)

# Global Neo4j driver instance
_neo4j_driver = None


async def init_neo4j(settings: Settings):
    """
    Initialize the Neo4j connection.
    
    Args:
        settings: Application settings
        
    Returns:
        The Neo4j driver
        
    Raises:
        DatabaseConnectionError: If connection fails
    """
    global _neo4j_driver
    
    try:
        # Create the Neo4j driver
        _neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        
        # Test the connection
        async with _neo4j_driver.session() as session:
            result = await session.run("RETURN 1 AS test")
            record = await result.single()
            
            if not record or record.get("test") != 1:
                raise DatabaseConnectionError("Neo4j connection test failed")
        
        logger.info(
            f"Neo4j connection initialized",
            extra={"uri": settings.neo4j_uri}
        )
        
        # Create initial schema constraints if needed
        await _create_schema_constraints()
        
        return _neo4j_driver
        
    except Exception as e:
        logger.exception(f"Failed to initialize Neo4j connection: {str(e)}")
        raise DatabaseConnectionError(f"Failed to connect to Neo4j: {str(e)}")


async def _create_schema_constraints():
    """
    Create schema constraints in Neo4j if they don't exist.
    
    Raises:
        DatabaseError: If constraint creation fails
    """
    try:
        async with _neo4j_driver.session() as session:
            # Create constraint on Procedure names (if using Neo4j 4.x+)
            try:
                await session.run(
                    "CREATE CONSTRAINT procedure_name_unique IF NOT EXISTS "
                    "FOR (p:Procedure) REQUIRE p.name IS UNIQUE"
                )
            except Neo4jError:
                # Fallback for older Neo4j versions
                await session.run(
                    "CREATE CONSTRAINT ON (p:Procedure) ASSERT p.name IS UNIQUE"
                )
                
            # Create constraint on Step IDs
            try:
                await session.run(
                    "CREATE CONSTRAINT step_id_unique IF NOT EXISTS "
                    "FOR (s:Step) REQUIRE s.id IS UNIQUE"
                )
            except Neo4jError:
                # Fallback for older Neo4j versions
                await session.run(
                    "CREATE CONSTRAINT ON (s:Step) ASSERT s.id IS UNIQUE"
                )
            
            logger.info("Neo4j schema constraints created")
            
    except Exception as e:
        logger.warning(f"Failed to create Neo4j schema constraints: {str(e)}")
        # Continue without failing - constraints are helpful but not critical


def get_neo4j_driver():
    """
    Get the Neo4j driver instance.
    
    Returns:
        The Neo4j driver
        
    Raises:
        DatabaseConnectionError: If Neo4j is not initialized
    """
    global _neo4j_driver
    
    if _neo4j_driver is None:
        raise DatabaseConnectionError("Neo4j is not initialized. Call init_neo4j first.")
    
    return _neo4j_driver


@log_execution_time(logger)
async def execute_query(
    query: str,
    params: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Execute a Cypher query against Neo4j.
    
    Args:
        query: Cypher query to execute
        params: Query parameters
        database: Optional database name
        
    Returns:
        List of result records as dictionaries
        
    Raises:
        DatabaseQueryError: If the query fails
    """
    global _neo4j_driver
    
    if _neo4j_driver is None:
        raise DatabaseConnectionError("Neo4j is not initialized. Call init_neo4j first.")
    
    try:
        # Execute the query
        async with _neo4j_driver.session(database=database) as session:
            result = await session.run(query, params or {})
            
            # Collect all records
            records = []
            async for record in result:
                # Convert record to dictionary
                record_dict = {}
                for key, value in record.items():
                    # Handle Neo4j types if needed
                    record_dict[key] = _convert_neo4j_types(value)
                
                records.append(record_dict)
            
            return records
            
    except Neo4jError as e:
        logger.error(
            f"Neo4j query error: {str(e)}",
            extra={
                "query": query,
                "params": params,
                "code": getattr(e, "code", None)
            }
        )
        raise DatabaseQueryError(f"Neo4j query error: {str(e)}")
    except Exception as e:
        logger.exception(
            f"Error executing Neo4j query: {str(e)}",
            extra={"query": query, "params": params}
        )
        raise DatabaseQueryError(f"Failed to execute Neo4j query: {str(e)}")


def _convert_neo4j_types(value: Any) -> Any:
    """
    Convert Neo4j-specific types to Python types.
    
    Args:
        value: Value to convert
        
    Returns:
        Converted value
    """
    # Handle different Neo4j types
    if hasattr(value, "items") and callable(getattr(value, "items")):
        # Convert Node or similar types to dictionary
        return {k: _convert_neo4j_types(v) for k, v in value.items()}
    elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes, bytearray)):
        # Convert iterables
        return [_convert_neo4j_types(v) for v in value]
    
    # Return as is for other types
    return value


@log_execution_time(logger)
async def create_procedure(
    name: str, 
    steps: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a procedure with steps in Neo4j.
    
    Args:
        name: Name of the procedure
        steps: List of step dictionaries
        metadata: Optional metadata for the procedure
        
    Returns:
        ID of the created procedure
        
    Raises:
        DatabaseError: If creation fails
    """
    try:
        # Create procedure query
        procedure_query = """
        MERGE (p:Procedure {name: $name})
        SET p.created_at = datetime(),
            p.updated_at = datetime(),
            p.metadata = $metadata
        RETURN p.name AS id
        """
        
        # Create procedure
        procedure_results = await execute_query(
            procedure_query,
            {"name": name, "metadata": json.dumps(metadata or {})}
        )
        
        if not procedure_results:
            raise DatabaseError(f"Failed to create procedure: {name}")
        
        procedure_id = procedure_results[0]["id"]
        
        # Create steps
        for i, step in enumerate(steps):
            step_id = step.get("id", f"{name}_step_{i}")
            description = step.get("description", "")
            action = step.get("action", "")
            
            # Create step query
            step_query = """
            MATCH (p:Procedure {name: $procedure_name})
            MERGE (s:Step {id: $step_id})
            SET s.description = $description,
                s.action = $action,
                s.order = $order,
                s.updated_at = datetime()
            MERGE (p)-[:HAS_STEP]->(s)
            RETURN s.id AS id
            """
            
            await execute_query(
                step_query,
                {
                    "procedure_name": name,
                    "step_id": step_id,
                    "description": description,
                    "action": action,
                    "order": i
                }
            )
        
        # Create NEXT relationships between steps
        for i in range(len(steps) - 1):
            current_step_id = steps[i].get("id", f"{name}_step_{i}")
            next_step_id = steps[i + 1].get("id", f"{name}_step_{i + 1}")
            
            relationship_query = """
            MATCH (curr:Step {id: $curr_id}), (next:Step {id: $next_id})
            MERGE (curr)-[:NEXT]->(next)
            """
            
            await execute_query(
                relationship_query,
                {"curr_id": current_step_id, "next_id": next_step_id}
            )
        
        logger.info(
            f"Created procedure in Neo4j: {name}",
            extra={"procedure_id": procedure_id, "step_count": len(steps)}
        )
        
        return procedure_id
        
    except (DatabaseQueryError, DatabaseConnectionError):
        # Re-raise these exceptions
        raise
    except Exception as e:
        logger.exception(f"Error creating procedure in Neo4j: {str(e)}")
        raise DatabaseError(f"Failed to create procedure: {str(e)}")


@log_execution_time(logger)
async def get_procedure(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a procedure with its steps from Neo4j.
    
    Args:
        name: Name of the procedure
        
    Returns:
        Procedure dictionary with steps, or None if not found
        
    Raises:
        DatabaseError: If retrieval fails
    """
    try:
        # Check if procedure exists
        procedure_query = """
        MATCH (p:Procedure {name: $name})
        RETURN p.name AS name, 
               p.created_at AS created_at, 
               p.updated_at AS updated_at, 
               p.metadata AS metadata
        """
        
        procedure_results = await execute_query(procedure_query, {"name": name})
        
        if not procedure_results:
            return None
        
        procedure = procedure_results[0]
        
        # Parse metadata JSON
        try:
            metadata = json.loads(procedure.get("metadata", "{}"))
        except json.JSONDecodeError:
            metadata = {}
        
        # Get steps
        steps_query = """
        MATCH (p:Procedure {name: $name})-[:HAS_STEP]->(s:Step)
        RETURN s.id AS id, 
               s.description AS description, 
               s.action AS action, 
               s.order AS order
        ORDER BY s.order
        """
        
        steps_results = await execute_query(steps_query, {"name": name})
        
        # Format procedure with steps
        procedure_data = {
            "name": procedure["name"],
            "created_at": procedure.get("created_at"),
            "updated_at": procedure.get("updated_at"),
            "metadata": metadata,
            "steps": steps_results
        }
        
        return procedure_data
        
    except (DatabaseQueryError, DatabaseConnectionError):
        # Re-raise these exceptions
        raise
    except Exception as e:
        logger.exception(f"Error getting procedure from Neo4j: {str(e)}")
        raise DatabaseError(f"Failed to get procedure: {str(e)}")


@log_execution_time(logger)
async def search_procedures(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for procedures in Neo4j.
    
    Args:
        query: Search query
        limit: Maximum number of results
        
    Returns:
        List of matching procedures
        
    Raises:
        DatabaseError: If search fails
    """
    try:
        # Try to use full-text search if available in Neo4j Enterprise
        try:
            # First attempt with full-text search
            search_query = """
            CALL db.index.fulltext.queryNodes("procedure_description", $query) 
            YIELD node, score
            WITH node AS p, score
            WHERE p:Procedure
            RETURN p.name AS name, score
            ORDER BY score DESC
            LIMIT $limit
            """
            
            search_results = await execute_query(
                search_query, 
                {"query": query, "limit": limit}
            )
            
            if search_results:
                # Full-text search worked, get the matching procedures
                procedure_names = [result["name"] for result in search_results]
            else:
                # If no results, try the fallback approach
                raise Neo4jError("No results from full-text search", "")
                
        except Neo4jError:
            # Fallback to CONTAINS for basic Neo4j editions
            search_query = """
            MATCH (p:Procedure)
            WHERE toLower(p.name) CONTAINS toLower($query) 
            RETURN p.name AS name
            LIMIT $limit
            """
            
            # Also try searching in steps
            search_steps_query = """
            MATCH (p:Procedure)-[:HAS_STEP]->(s:Step)
            WHERE toLower(s.description) CONTAINS toLower($query)
            RETURN DISTINCT p.name AS name
            LIMIT $limit
            """
            
            # Execute both queries
            name_results = await execute_query(search_query, {"query": query, "limit": limit})
            step_results = await execute_query(search_steps_query, {"query": query, "limit": limit})
            
            # Combine results, removing duplicates
            procedure_names = []
            seen = set()
            
            for result in name_results + step_results:
                name = result["name"]
                if name not in seen:
                    procedure_names.append(name)
                    seen.add(name)
                    
                if len(procedure_names) >= limit:
                    break
        
        # Get the full details of each procedure
        procedures = []
        for name in procedure_names:
            procedure = await get_procedure(name)
            if procedure:
                procedures.append(procedure)
            
            if len(procedures) >= limit:
                break
                
        return procedures
        
    except (DatabaseQueryError, DatabaseConnectionError):
        # Re-raise these exceptions
        raise
    except Exception as e:
        logger.exception(f"Error searching procedures in Neo4j: {str(e)}")
        raise DatabaseError(f"Failed to search procedures: {str(e)}")


@log_execution_time(logger)
async def delete_procedure(name: str) -> bool:
    """
    Delete a procedure and its steps from Neo4j.
    
    Args:
        name: Name of the procedure
        
    Returns:
        True if the procedure was deleted, False if not found
        
    Raises:
        DatabaseError: If deletion fails
    """
    try:
        # Check if procedure exists
        procedure_query = """
        MATCH (p:Procedure {name: $name})
        RETURN count(p) AS count
        """
        
        procedure_results = await execute_query(procedure_query, {"name": name})
        
        if not procedure_results or procedure_results[0]["count"] == 0:
            return False
        
        # Delete procedure and its steps
        delete_query = """
        MATCH (p:Procedure {name: $name})
        OPTIONAL MATCH (p)-[:HAS_STEP]->(s:Step)
        DETACH DELETE p, s
        """
        
        await execute_query(delete_query, {"name": name})
        
        logger.info(f"Deleted procedure from Neo4j: {name}")
        
        return True
        
    except (DatabaseQueryError, DatabaseConnectionError):
        # Re-raise these exceptions
        raise
    except Exception as e:
        logger.exception(f"Error deleting procedure from Neo4j: {str(e)}")
        raise DatabaseError(f"Failed to delete procedure: {str(e)}")


async def close():
    """
    Close the Neo4j driver.
    
    This function should be called when shutting down the application
    to release resources properly.
    """
    global _neo4j_driver
    
    if _neo4j_driver is not None:
        try:
            await _neo4j_driver.close()
            logger.info("Neo4j connection closed")
        except Exception as e:
            logger.error(f"Error closing Neo4j connection: {str(e)}")
        
        _neo4j_driver = None