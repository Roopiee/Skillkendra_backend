"""
History API endpoints
"""

from fastapi import APIRouter, Query
from typing import Optional
from src.database.models import get_history

router = APIRouter()


@router.get("/")
async def get_recent_activity(limit: int = Query(10, ge=1, le=50)):
    """Get recent verification activity"""
    history = get_history()
    recent = history.get_recent(limit=limit)
    
    return {
        "success": True,
        "count": len(recent),
        "verifications": recent
    }


@router.get("/stats")
async def get_statistics():
    """Get verification statistics"""
    history = get_history()
    stats = history.get_stats()
    
    return {
        "success": True,
        "stats": stats
    }


@router.get("/search")
async def search_history(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100)
):
    """Search verification history"""
    history = get_history()
    results = history.search(query=q, limit=limit)
    
    return {
        "success": True,
        "query": q,
        "count": len(results),
        "results": results
    }
