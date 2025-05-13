# filepath: backend/services/memory/procedural.py
"""
Procedural memory implementation using Neo4j graph database.

This module implements procedural memory for storing and retrieving action
sequences and workflows as graph structures.
"""
import json
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio

import neo4j
from neo4j import GraphDatabase, AsyncGraphDatabase, exceptions

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    MemoryError, MemoryStorageError, MemoryRetrievalError, 
    DatabaseConnectionError
)
from app.config import Settings
from app.services.memory.base import MemorySystem, MemoryItem


logger = get_logger(__name__)

class ProceduralMemory(MemorySystem[Dict[str, Any]]):
    """
    Procedural memory implementation using Neo4j.
    
    This class:
    1. Stores step-by-step procedures and workflows as graph structures
    2. Retrieves procedures by name or purpose
    3. Supports understanding how to perform multi-step actions
    
    It uses Neo4j graph database to represent procedural knowledge.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize procedural memory with Neo4j connection.
        
        Args:
            settings: Application configuration settings
            
        Raises:
            DatabaseConnectionError: If Neo4j connection fails
        """
        super().__init__("procedural")
        self.settings = settings
        
        # Initialize Neo4j connection
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            
            self.logger.info(
                f"Initialized procedural memory with Neo4j at {settings.neo4j_uri}"
            )
            
        except Exception as e:
            self.logger.exception("Failed to initialize Neo4j connection")
            raise DatabaseConnectionError(f"Neo4j connection failed: {str(e)}")
    
    async def _ensure_constraints(self):
        """
        Ensure all required constraints and indexes exist.
        
        This method creates any necessary constraints and indexes for the graph.
        """
        try:
            async with self.driver.session() as session:
                # Create constraint on Procedure names
                await session.run(
                    "CREATE CONSTRAINT procedure_name IF NOT EXISTS "
                    "FOR (p:Procedure) REQUIRE p.name IS UNIQUE"
                )
                
                # Create constraint on Step IDs
                await session.run(
                    "CREATE CONSTRAINT step_id IF NOT EXISTS "
                    "FOR (s:Step) REQUIRE s.id IS UNIQUE"
                )
                
                # Create index on Step orders within procedures
                await session.run(
                    "CREATE INDEX step_order IF NOT EXISTS "
                    "FOR (s:Step) ON (s.order)"
                )
                
                # Create index on Step descriptions for text search
                await session.run(
                    "CREATE INDEX step_description IF NOT EXISTS "
                    "FOR (s:Step) ON (s.description)"
                )
                
                self.logger.debug("Ensured constraints and indexes for procedural memory")
                
        except Exception as e:
            self.logger.warning(f"Failed to create constraints or indexes: {str(e)}")
    
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
            The key (procedure name) used to store the procedure
            
        Raises:
            MemoryStorageError: If storing fails
        """
        try:
            # Ensure constraints
            await self._ensure_constraints()
            
            # Extract procedure information
            procedure_name = key
            steps = content.get("steps", [])
            
            if not steps:
                raise ValueError("Procedure must contain at least one step")
            
            # Ensure metadata is a dictionary
            if metadata is None:
                metadata = {}
            
            # Create procedure and steps
            async with self.driver.session() as session:
                # Create procedure node
                await session.run(
                    """
                    MERGE (p:Procedure {name: $name})
                    SET p.created_at = datetime(),
                        p.updated_at = datetime(),
                        p.metadata = $metadata
                    RETURN p
                    """,
                    name=procedure_name,
                    metadata=json.dumps(metadata)
                )
                
                # Create step nodes and relationships
                for i, step in enumerate(steps):
                    step_id = step.get("id", f"{procedure_name}_step_{i}")
                    description = step.get("description", "")
                    action = step.get("action", "")
                    
                    # Create step node
                    await session.run(
                        """
                        MATCH (p:Procedure {name: $procedure_name})
                        MERGE (s:Step {id: $step_id})
                        SET s.description = $description,
                            s.action = $action,
                            s.order = $order,
                            s.updated_at = datetime()
                        MERGE (p)-[:HAS_STEP]->(s)
                        """,
                        procedure_name=procedure_name,
                        step_id=step_id,
                        description=description,
                        action=action,
                        order=i
                    )
                
                # Create NEXT relationships between steps
                for i in range(len(steps) - 1):
                    current_step_id = steps[i].get("id", f"{procedure_name}_step_{i}")
                    next_step_id = steps[i + 1].get("id", f"{procedure_name}_step_{i + 1}")
                    
                    await session.run(
                        """
                        MATCH (curr:Step {id: $curr_id}), (next:Step {id: $next_id})
                        MERGE (curr)-[:NEXT]->(next)
                        """,
                        curr_id=current_step_id,
                        next_id=next_step_id
                    )
            
            self.logger.debug(
                f"Stored procedure in procedural memory: {procedure_name}",
                extra={"step_count": len(steps)}
            )
            
            return procedure_name
            
        except neo4j.exceptions.Neo4jError as e:
            self.logger.exception(f"Neo4j error storing procedure: {key}")
            raise MemoryStorageError(f"Failed to store in procedural memory: {str(e)}")
        except Exception as e:
            self.logger.exception(f"Unexpected error storing procedure: {key}")
            raise MemoryStorageError(f"Failed to store in procedural memory: {str(e)}")
    
    @log_execution_time(logger)
    async def retrieve(self, key: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Retrieve a procedure from procedural memory by name.
        
        Args:
            key: The name of the procedure to retrieve
            **kwargs: Additional parameters
            
        Returns:
            The procedure with steps, or None if not found
            
        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        try:
            async with self.driver.session() as session:
                # Check if procedure exists
                procedure_result = await session.run(
                    "MATCH (p:Procedure {name: $name}) RETURN p",
                    name=key
                )
                
                procedure_record = await procedure_result.single()
                if not procedure_record:
                    return None
                
                # Get procedure metadata
                procedure = procedure_record["p"]
                procedure_data = {
                    "name": procedure.get("name"),
                    "created_at": procedure.get("created_at"),
                    "updated_at": procedure.get("updated_at"),
                    "metadata": json.loads(procedure.get("metadata", "{}"))
                }
                
                # Get steps
                steps_result = await session.run(
                    """
                    MATCH (p:Procedure {name: $name})-[:HAS_STEP]->(s:Step)
                    RETURN s
                    ORDER BY s.order
                    """,
                    name=key
                )
                
                steps = []
                async for record in steps_result:
                    step = record["s"]
                    step_data = {
                        "id": step.get("id"),
                        "description": step.get("description", ""),
                        "action": step.get("action", ""),
                        "order": step.get("order", 0)
                    }
                    steps.append(step_data)
                
                procedure_data["steps"] = steps
                
                return procedure_data
                
        except neo4j.exceptions.Neo4jError as e:
            self.logger.exception(f"Neo4j error retrieving procedure: {key}")
            raise MemoryRetrievalError(f"Failed to retrieve from procedural memory: {str(e)}")
        except Exception as e:
            self.logger.exception(f"Unexpected error retrieving procedure: {key}")
            raise MemoryRetrievalError(f"Failed to retrieve from procedural memory: {str(e)}")
    
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
            List of matching procedures with steps
            
        Raises:
            MemoryRetrievalError: If search fails
        """
        try:
            async with self.driver.session() as session:
                # Use full-text search if available, otherwise use CONTAINS
                try:
                    # Try full-text search first (requires Neo4j Enterprise)
                    procedures_result = await session.run(
                        """
                        CALL db.index.fulltext.queryNodes("step_description", $query) 
                        YIELD node, score
                        MATCH (p:Procedure)-[:HAS_STEP]->(node)
                        RETURN DISTINCT p.name AS procedure_name, score
                        ORDER BY score DESC
                        LIMIT $limit
                        """,
                        query=query,
                        limit=limit
                    )
                    
                    procedures = await procedures_result.values()
                    
                    if procedures:
                        procedure_names = [row[0] for row in procedures]
                    else:
                        # Fall back to CONTAINS if no results
                        raise Exception("No results from full-text search")
                
                except Exception:
                    # Fall back to CONTAINS for regular Neo4j
                    procedures_result = await session.run(
                        """
                        MATCH (p:Procedure)-[:HAS_STEP]->(s:Step)
                        WHERE toLower(s.description) CONTAINS toLower($query) 
                           OR toLower(p.name) CONTAINS toLower($query)
                        RETURN DISTINCT p.name AS procedure_name
                        LIMIT $limit
                        """,
                        query=query.lower(),
                        limit=limit
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
                procedure_result = await session.run(
                    "MATCH (p:Procedure {name: $name}) RETURN p",
                    name=key
                )
                
                procedure_record = await procedure_result.single()
                if not procedure_record:
                    return False
                
                # Delete procedure and all its steps
                delete_result = await session.run(
                    """
                    MATCH (p:Procedure {name: $name})
                    OPTIONAL MATCH (p)-[:HAS_STEP]->(s:Step)
                    DETACH DELETE p, s
                    """,
                    name=key
                )
                
                # Deletion always succeeds if the procedure exists
                self.logger.debug(f"Deleted procedure from procedural memory: {key}")
                
                return True
                
        except neo4j.exceptions.Neo4jError as e:
            self.logger.exception(f"Neo4j error deleting procedure: {key}")
            raise MemoryError(f"Failed to delete from procedural memory: {str(e)}")
        except Exception as e:
            self.logger.exception(f"Unexpected error deleting procedure: {key}")
            raise MemoryError(f"Failed to delete from procedural memory: {str(e)}")
    
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