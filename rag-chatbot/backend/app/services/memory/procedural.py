"""
Procedural memory implementation using Neo4j graph database.

This module provides a procedural memory system that stores and retrieves
procedures as graph structures in a Neo4j database. Each procedure consists
of a sequence of steps with relationships between them.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast

import neo4j
from neo4j import AsyncGraphDatabase, AsyncSession, AsyncTransaction

from app.config import Settings
from app.core.exceptions import (
    DatabaseConnectionError,
    MemoryError,
    MemoryRetrievalError,
    MemoryStorageError,
)
from app.core.logging import get_logger, log_execution_time
from app.services.memory.base import MemorySystem, MemoryItem

# Type aliases for better code readability
ProcedureData = Dict[str, Any]
ProcedureStep = Dict[str, Any]
ProcedureMetadata = Dict[str, Any]

logger = get_logger(__name__)

# Constants for Neo4j node and relationship types
NODE_PROCEDURE = "Procedure"
NODE_STEP = "Step"
RELATION_NEXT = "NEXT"
RELATION_FIRST = "FIRST_STEP"
RELATION_LAST = "LAST_STEP"

# Query templates for better maintainability
QUERY_CREATE_PROCEDURE = """
MERGE (p:Procedure {name: $name})
SET p.description = $description,
    p.created_at = datetime(),
    p.updated_at = datetime(),
    p.metadata = $metadata
RETURN id(p) as id
"""

QUERY_CREATE_STEP = """
MATCH (p:Procedure {name: $procedure_name})
CREATE (s:Step {
    id: $step_id,
    action: $action,
    parameters: $parameters,
    order: $order,
    created_at: datetime()
})
WITH p, s
WHERE $is_first
CREATE (p)-[:FIRST_STEP]->(s)
WITH p, s
WHERE $is_last
CREATE (p)-[:LAST_STEP]->(s)
RETURN id(s) as id
"""

QUERY_LINK_STEPS = """
MATCH (s1:Step {id: $step1_id}), (s2:Step {id: $step2_id})
CREATE (s1)-[:NEXT]->(s2)
"""

class ProceduralMemory(MemorySystem[Dict[str, Any]]):
    """
    Procedural memory implementation using Neo4j.
    
    This class provides methods to store, retrieve, and manage procedures
    as directed graphs in a Neo4j database. Each procedure is represented
    as a sequence of steps with relationships between them.
    
    Attributes:
        driver: Neo4j async driver instance
        settings: Application configuration settings
        logger: Logger instance for the class
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize procedural memory with Neo4j connection.
        
        Args:
            settings: Application configuration settings with Neo4j credentials
            
        Raises:
            DatabaseConnectionError: If Neo4j connection fails
        """
        super().__init__("procedural")
        self.settings = settings
        self.logger = logger
        self.driver = self._initialize_driver()
        
        # Ensure constraints and indexes exist
        asyncio.create_task(self._ensure_constraints())
    
    def _initialize_driver(self) -> AsyncGraphDatabase.driver:
        """Initialize and return a Neo4j async driver.
        
        Returns:
            AsyncGraphDatabase.driver: Initialized Neo4j driver
            
        Raises:
            DatabaseConnectionError: If connection fails
        """
        try:
            driver = AsyncGraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(
                    self.settings.neo4j_user,
                    self.settings.neo4j_password
                ),
                max_connection_lifetime=3600,
                connection_timeout=30,
                connection_acquisition_timeout=60,
                max_connection_pool_size=50,
            )
            
            self.logger.info(
                "Initialized procedural memory with Neo4j at %s",
                self.settings.neo4j_uri
            )
            return driver
            
        except Exception as e:
            self.logger.exception("Failed to initialize Neo4j connection")
            raise DatabaseConnectionError(
                f"Neo4j connection failed: {str(e)}"
            ) from e
    
    async def _ensure_constraints(self) -> None:
        """
        Ensure all required constraints and indexes exist.
        
        This method creates any necessary constraints and indexes for the graph.
        
        Raises:
            MemoryError: If creating constraints or indexes fails
        """
        constraints = [
            # Unique constraint on procedure name
            {
                "query": """
                    CREATE CONSTRAINT procedure_name IF NOT EXISTS
                    FOR (p:Procedure) REQUIRE p.name IS UNIQUE
                    """,
                "name": "procedure_name"
            },
            # Index on step id for faster lookups
            {
                "query": """
                    CREATE INDEX step_id IF NOT EXISTS
                    FOR (s:Step) ON (s.id)
                    """,
                "name": "step_id"
            },
            # Index on procedure timestamps for sorting
            {
                "query": """
                    CREATE INDEX procedure_created_at IF NOT EXISTS
                    FOR (p:Procedure) ON (p.created_at)
                    """,
                "name": "procedure_created_at"
            },
            {
                "query": """
                    CREATE INDEX procedure_updated_at IF NOT EXISTS
                    FOR (p:Procedure) ON (p.updated_at)
                    """,
                "name": "procedure_updated_at"
            }
        ]
        
        try:
            async with self.driver.session() as session:
                for constraint in constraints:
                    try:
                        await session.run(constraint["query"])
                        self.logger.debug(
                            "Ensured constraint/index: %s", constraint["name"]
                        )
                    except Exception as e:
                        self.logger.warning(
                            "Failed to create constraint/index %s: %s",
                            constraint["name"], str(e)
                        )
                        # Continue with other constraints/indexes even if one fails
                        continue
                
                self.logger.info("Completed ensuring constraints and indexes")
                
        except Exception as e:
            self.logger.exception("Failed to ensure constraints and indexes")
            raise MemoryError(f"Failed to ensure constraints: {str(e)}") from e
            
    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if hasattr(self, 'driver'):
            await self.driver.close()
            self.logger.info("Closed Neo4j driver connection")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    @log_execution_time(logger)
    async def store(
        self, 
        key: str, 
        content: Dict[str, Any], 
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Store a procedure in procedural memory.
        
        Args:
            key: Name of the procedure
            content: Dictionary with 'steps' list of ordered actions
            metadata: Additional metadata for the procedure
            **kwargs: Additional parameters
            
        Returns:
            str: The key (procedure name) used to store the procedure
            
        Raises:
            ValueError: If required fields are missing
            MemoryStorageError: If storing fails
        """
        if not key:
            raise ValueError("Procedure name cannot be empty")
            
        if not content or not isinstance(content.get('steps'), list):
            raise ValueError("Content must contain a 'steps' list")
            
        metadata = metadata or {}
        steps = content['steps']
        
        try:
            async with self.driver.session() as session:
                # Store the procedure
                result = await session.execute_write(
                    lambda tx: tx.run(
                        QUERY_CREATE_PROCEDURE,
                        name=key,
                        description=content.get('description', ''),
                        metadata=json.dumps(metadata)
                    )
                )
                
                # Store steps and their relationships
                prev_step_id = None
                for i, step in enumerate(steps):
                    step_id = step.get('id', str(uuid.uuid4()))
                    is_first = i == 0
                    is_last = i == len(steps) - 1
                    
                    # Create step node
                    await session.execute_write(
                        lambda tx: tx.run(
                            QUERY_CREATE_STEP,
                            procedure_name=key,
                            step_id=step_id,
                            action=step.get('action', ''),
                            parameters=json.dumps(step.get('parameters', {})),
                            order=i,
                            is_first=is_first,
                            is_last=is_last
                        )
                    )
                    
                    # Link to previous step if exists
                    if prev_step_id:
                        await session.execute_write(
                            lambda tx: tx.run(
                                QUERY_LINK_STEPS,
                                step1_id=prev_step_id,
                                step2_id=step_id
                            )
                        )
                    
                    prev_step_id = step_id
                
                self.logger.debug("Stored procedure: %s with %d steps", key, len(steps))
                return key
                
        except Exception as e:
            self.logger.exception("Failed to store procedure: %s", key)
            raise MemoryStorageError(f"Failed to store procedure: {str(e)}") from e
    
    @log_execution_time(logger)
    async def retrieve(self, key: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Retrieve a procedure from procedural memory by name.
        
        Args:
            key: The name of the procedure to retrieve
            **kwargs: Additional parameters
            
        Returns:
            Optional[Dict[str, Any]]: The procedure with steps, or None if not found
            
        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        query = """
        MATCH (p:Procedure {name: $name})
        OPTIONAL MATCH (p)-[:FIRST_STEP]->(first:Step)
        OPTIONAL MATCH path = (first)-[:NEXT*0..]->(last:Step)
        RETURN p, collect(nodes(path)), collect(relationships(path))
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, name=key)
                record = await result.single()
                
                if not record or not record[0]:
                    return None
                
                # Reconstruct the procedure with steps in order
                procedure = dict(record[0])
                steps = []
                
                # Get all step nodes from the path
                step_nodes = []
                for node_list in record[1]:
                    step_nodes.extend(node_list)
                
                # Sort steps by order property
                step_nodes = sorted(
                    [node for node in step_nodes if 'Step' in dict(node.labels)],
                    key=lambda x: x['order']
                )
                
                for step_node in step_nodes:
                    step = dict(step_node)
                    if 'parameters' in step and isinstance(step['parameters'], str):
                        step['parameters'] = json.loads(step['parameters'])
                    steps.append(step)
                
                procedure['steps'] = steps
                return procedure
                
        except Exception as e:
            self.logger.exception("Failed to retrieve procedure: %s", key)
            raise MemoryRetrievalError(f"Failed to retrieve procedure: {str(e)}") from e
    
    @log_execution_time(logger)
    async def search(
        self, 
        query: str, 
        limit: int = 5, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for procedures in procedural memory.
        
        Args:
            query: The search query
            limit: Maximum number of procedures to return
            **kwargs: Additional parameters
            
        Returns:
            List[Dict[str, Any]]: List of matching procedures with steps
            
        Raises:
            MemoryRetrievalError: If search fails
        """
        try:
            async with self.driver.session() as session:
                # Use full-text search if available, otherwise use CONTAINS
                try:
                    # Try full-text search first (requires Neo4j Enterprise)
                    # First check if full-text index exists
                    index_check = await session.run(
                        """
                        CALL db.indexes() YIELD name, type, entityType, labelsOrTypes, properties
                        WHERE type = 'FULLTEXT' AND 'step_description' IN name
                        RETURN count(*) > 0 as has_index
                        """
                    )
                    has_index = await index_check.single()
                    
                    if has_index and has_index["has_index"]:
                        procedures_result = await session.run(
                            """
                            CALL db.index.fulltext.queryNodes("step_description", $query) 
                            YIELD node, score
                            MATCH (p:Procedure)-[:HAS_STEP]->(node)
                            RETURN DISTINCT p.name AS procedure_name, score
                            ORDER BY score DESC
                            LIMIT $limit
                            """,
                            {"query": query, "limit": limit}
                        )
                        procedures = await procedures_result.values()
                        procedure_names = [row[0] for row in procedures]
                    else:
                        # If full-text index doesn't exist, use CONTAINS search
                        raise Exception("Full-text index not found")
                except Exception as e:
                    self.logger.warning(f"Full-text search failed: {str(e)}")
                    # Fallback to CONTAINS search if full-text search fails
                    # Fallback to CONTAINS search
                    procedures_result = await session.run(
                        """
                        MATCH (p:Procedure)-[:HAS_STEP]->(s:Step)
                        WHERE toLower(s.description) CONTAINS toLower($query) 
                           OR toLower(p.name) CONTAINS toLower($query)
                        RETURN DISTINCT p.name AS procedure_name
                        ORDER BY p.name
                        LIMIT $limit
                        """,
                        {"query": query.lower(), "limit": limit}
                    )
                    
                    values = await procedures_result.values()
                    procedure_names = [row[0] for row in values]
                
                # Retrieve full procedure data for each match
                results = []
                for procedure_name in procedure_names:
                    procedure_data = await self.retrieve(procedure_name)
                    if procedure_data:
                        results.append(procedure_data)
                
                self.logger.debug(
                    f"Procedural search results for query: {query[:50]}...",
                    extra={"query": query, "result_count": len(results)}
                )
                
                return results
                
        except neo4j.exceptions.Neo4jError as e:
            self.logger.exception(f"Neo4j error searching procedures: {query[:50]}...")
            raise MemoryRetrievalError(f"Failed to search procedural memory: {str(e)}")
        except Exception as e:
            self.logger.exception(f"Unexpected error searching procedures: {query[:50]}...")
            raise MemoryRetrievalError(f"Failed to search procedural memory: {str(e)}")
    
    @log_execution_time(logger)
    async def delete(self, key: str, **kwargs) -> bool:
        """
        Delete a procedure from procedural memory.

        Args:
            key: The name of the procedure to delete
            **kwargs: Additional parameters

        Returns:
            True if procedure was deleted, False otherwise

        Raises:
            MemoryError: If deletion fails
        """
        try:
            async with self.driver.session() as session:
                # Check if procedure exists
                procedure_count = await session.execute_read(
                    lambda tx: tx.run(
                        """
                        MATCH (p:Procedure {name: $name})
                        RETURN count(p) as count
                        """,
                        name=key,
                    ).single()["count"]
                )

                if procedure_count == 0:
                    return False

                # Delete the procedure and its relationships
                await session.execute_write(
                    lambda tx: tx.run(
                        """
                        MATCH (p:Procedure {name: $name})
                        DETACH DELETE p
                        """,
                        name=key,
                    )
                )

                self.logger.debug(
                    "Deleted procedure from procedural memory: %s", key
                )
                return True

        except neo4j.exceptions.Neo4jError as e:
            self.logger.exception("Neo4j error deleting procedure: %s", key)
            raise MemoryError(f"Failed to delete procedure: {str(e)}")
        except Exception as e:
            self.logger.exception("Unexpected error deleting procedure: %s", key)
            raise MemoryError(f"Failed to delete procedure: {str(e)}")
    
    @log_execution_time(logger)
    async def clear(self, **kwargs) -> None:
        """
        Clear all procedures from procedural memory.
        
        Args:
            **kwargs: Additional parameters
            
        Raises:
            MemoryError: If clearing fails
        """
        try:
            async with self.driver.session() as session:
                # Delete all procedures and steps
                await session.run(
                    """
                    MATCH (p:Procedure)
                    OPTIONAL MATCH (p)-[:HAS_STEP]->(s:Step)
                    DETACH DELETE p, s
                    """
                )
                
                self.logger.info("Cleared all procedural memory")
                
        except neo4j.exceptions.Neo4jError as e:
            self.logger.exception("Neo4j error clearing procedural memory")
            raise MemoryError(f"Failed to clear procedural memory: {str(e)}")
        except Exception as e:
            self.logger.exception("Unexpected error clearing procedural memory")
            raise MemoryError(f"Failed to clear procedural memory: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if Neo4j connection is healthy.
        
        Returns:
            True if the connection is healthy, False otherwise
        """
        try:
            if not self.driver:
                return False
                
            async with self.driver.session() as session:
                # Simple query to check connection
                result = await session.run("RETURN 1 AS result")
                record = await result.single()
                return record and record["result"] == 1
                
        except Exception as e:
            self.logger.error(f"Neo4j health check failed: {str(e)}")
            return False
    
    async def close(self) -> None:
        """
        Close the Neo4j connection.
        
        This method should be called when shutting down the application
        to release resources properly.
        """
        try:
            await self.driver.close()
            self.logger.info("Closed procedural memory (Neo4j)")
        except Exception as e:
            self.logger.exception(f"Error closing procedural memory: {str(e)}")