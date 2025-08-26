from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
from ..services.simple_queue import simple_queue
from ..services.memory_queue import memory_queue
from ..services.redis_queue.redis_queue import redis_queue

router = APIRouter(prefix="/queue", tags=["队列状态"])

@router.get("/simple/stats")
async def get_simple_queue_stats() -> Dict[str, Any]:
    """获取简单内存队列统计信息"""
    return simple_queue.get_stats()

@router.get("/memory/stats")
async def get_memory_queue_stats() -> Dict[str, Any]:
    """获取内存队列统计信息"""
    return memory_queue.get_stats()

@router.get("/redis/stats")
async def get_redis_queue_stats() -> Dict[str, Any]:
    """获取Redis队列统计信息"""
    return redis_queue.get_stats()

@router.get("/stats")
async def get_all_queue_stats() -> Dict[str, Any]:
    """获取所有队列统计信息"""
    return {
        "simple_queue": simple_queue.get_stats(),
        "memory_queue": memory_queue.get_stats(),
        "redis_queue": redis_queue.get_stats()
    }

@router.post("/simple/clear/{topic}")
async def clear_simple_queue(topic: str) -> Dict[str, str]:
    """清空简单内存队列"""
    simple_queue.clear_queue(topic)
    return {"message": f"队列 {topic} 已清空"}

@router.post("/memory/clear/{topic}")
async def clear_memory_queue(topic: str) -> Dict[str, str]:
    """清空内存队列"""
    memory_queue.clear_queue(topic)
    return {"message": f"队列 {topic} 已清空"}

@router.post("/redis/clear/{topic}")
async def clear_redis_queue(topic: str) -> Dict[str, str]:
    """清空Redis队列"""
    await redis_queue.clear_queue(topic)
    return {"message": f"队列 {topic} 已清空"}