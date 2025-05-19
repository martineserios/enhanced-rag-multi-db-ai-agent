"""
Debug endpoints for troubleshooting MongoDB and memory system issues.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
import logging
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.mongo_client import MongoClient

from app.config import get_settings, Settings
from app.services.memory.manager import get_memory_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/mongo/collections")
async def list_mongo_collections(settings: Settings = Depends(get_settings)):
    """List all collections in the MongoDB database."""
    try:
        memory_manager = get_memory_manager()
        if "episodic" not in memory_manager.memory_systems:
            return {"error": "Episodic memory system not found"}
            
        mongo_db: Database = memory_manager.memory_systems["episodic"].db
        collections = await mongo_db.list_collection_names()
        
        result = {"collections": []}
        for coll_name in collections:
            coll: Collection = mongo_db[coll_name]
            count = await coll.count_documents({})
            result["collections"].append({
                "name": coll_name,
                "count": count,
                "indexes": await coll.index_information()
            })
            
        return result
        
    except Exception as e:
        logger.exception("Error listing MongoDB collections")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mongo/conversations/sample")
async def get_conversation_sample(limit: int = 5, settings: Settings = Depends(get_settings)):
    """Get a sample of conversation documents from the episodic memory."""
    try:
        memory_manager = get_memory_manager()
        if "episodic" not in memory_manager.memory_systems:
            return {"error": "Episodic memory system not found"}
            
        coll: Collection = memory_manager.memory_systems["episodic"].db["episodic_memory"]
        
        # Get a sample of documents
        pipeline = [
            {"$match": {"conversation_id": {"$exists": True}}},
            {"$limit": limit}
        ]
        
        cursor = coll.aggregate(pipeline)
        docs = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for doc in docs:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
                
        return {"documents": docs}
        
    except Exception as e:
        logger.exception("Error fetching conversation sample")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mongo/conversations/count")
async def count_conversations(settings: Settings = Depends(get_settings)):
    """Count conversations in the episodic memory."""
    try:
        memory_manager = get_memory_manager()
        if "episodic" not in memory_manager.memory_systems:
            return {"error": "Episodic memory system not found"}
            
        coll: Collection = memory_manager.memory_systems["episodic"].db["episodic_memory"]
        
        # Count distinct conversation_ids
        pipeline = [
            {"$match": {"conversation_id": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$conversation_id"}},
            {"$count": "total_conversations"}
        ]
        
        result = await coll.aggregate(pipeline).to_list(length=1)
        
        total = result[0]["total_conversations"] if result else 0
        
        return {
            "total_conversations": total,
            "total_documents": await coll.count_documents({})
        }
        
    except Exception as e:
        logger.exception("Error counting conversations")
        raise HTTPException(status_code=500, detail=str(e))
