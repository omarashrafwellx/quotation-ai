"""
Redis operations manager for queue and cache management.
"""

import json
import time
import uuid
from typing import Optional, Dict, Any, List
import redis.asyncio as redis
from pydantic import BaseModel
from src.core.config import settings
from src.core.constants import RedisKeys, ProcessingStates
from src.core.exceptions import StorageError

class EmailTask(BaseModel):
    task_id: str
    email_data: dict
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: str = ProcessingStates.QUEUED
    result: Optional[dict] = None
    error: Optional[str] = None

class ProcessingStats(BaseModel):
    total_queued: int = 0
    total_processed: int = 0
    currently_processing: int = 0
    queue_size: int = 0
    completed_count: int = 0
    failed_count: int = 0

class RedisManager:
    """Manages Redis operations for queue and cache."""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis_client: Optional[redis.Redis] = None
        self.redis_pubsub: Optional[redis.client.PubSub] = None
    
    async def connect(self) -> None:
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_pubsub = self.redis_client.pubsub()
            
            # Test connection
            await self.redis_client.ping()
            print("✅ Redis connection established")
            
            # Initialize stats if they don't exist
            if not await self.redis_client.exists(RedisKeys.STATS_KEY):
                stats = ProcessingStats()
                await self.redis_client.hset(RedisKeys.STATS_KEY, mapping=stats.model_dump())
                
        except Exception as e:
            raise StorageError(f"Redis connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Close Redis connections."""
        if self.redis_pubsub:
            await self.redis_pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
    
    async def update_stats(self, field: str, value: int, increment: bool = False) -> None:
        """Update processing statistics in Redis."""
        try:
            if increment:
                await self.redis_client.hincrby(RedisKeys.STATS_KEY, field, value)
            else:
                await self.redis_client.hset(RedisKeys.STATS_KEY, field, value)
        except Exception as e:
            print(f"Error updating stats: {e}")
    
    async def get_processing_stats(self) -> ProcessingStats:
        """Get current processing statistics."""
        try:
            stats_data = await self.redis_client.hgetall(RedisKeys.STATS_KEY)
            if stats_data:
                return ProcessingStats(**{k: int(v) for k, v in stats_data.items()})
            return ProcessingStats()
        except Exception as e:
            print(f"Error getting stats: {e}")
            return ProcessingStats()
    
    async def add_email_to_queue(self, email_data: dict) -> str:
        """Add email to processing queue."""
        task_id = str(uuid.uuid4())
        task = EmailTask(
            task_id=task_id,
            email_data=email_data,
            created_at=time.time(),
            status=ProcessingStates.QUEUED
        )
        
        try:
            # Add to queue
            await self.redis_client.lpush(RedisKeys.QUEUE_KEY, json.dumps(task.dict()))
            
            # Update stats
            await self.update_stats("total_queued", 1, increment=True)
            queue_size = await self.redis_client.llen(RedisKeys.QUEUE_KEY)
            await self.update_stats("queue_size", queue_size)
            
            email_from = email_data.get("from_email", "unknown")
            print(f"📥 Queued email for processing from {email_from} - Task ID: {task_id}")
            
            return task_id
            
        except Exception as e:
            raise StorageError(f"Error adding email to queue: {e}")
    
    async def get_next_email_from_queue(self) -> Optional[EmailTask]:
        """Get next email from queue (blocking)."""
        try:
            # Blocking pop from right side of list (FIFO)
            result = await self.redis_client.brpop(RedisKeys.QUEUE_KEY, timeout=1)
            if result:
                _, task_data = result
                task_dict = json.loads(task_data)
                return EmailTask(**task_dict)
            return None
        except Exception as e:
            print(f"Error getting email from queue: {e}")
            return None
    
    async def move_task_to_processing(self, task: EmailTask) -> None:
        """Move task from queue to processing state."""
        try:
            task.status = ProcessingStates.PROCESSING
            task.started_at = time.time()
            
            # Add to processing set
            await self.redis_client.hset(RedisKeys.PROCESSING_KEY, task.task_id, json.dumps(task.dict()))
            
            # Update stats
            processing_count = await self.redis_client.hlen(RedisKeys.PROCESSING_KEY)
            queue_size = await self.redis_client.llen(RedisKeys.QUEUE_KEY)
            await self.update_stats("currently_processing", processing_count)
            await self.update_stats("queue_size", queue_size)
            
            print(f"📤 Started processing task {task.task_id[:8]} from {task.email_data.get('from_email', 'unknown')}")
            
        except Exception as e:
            raise StorageError(f"Error moving task to processing: {e}")
    
    async def complete_task(self, task_id: str, result: dict = None, error: str = None) -> None:
        """Mark task as completed and clean up."""
        try:
            # Get task from processing
            task_data = await self.redis_client.hget(RedisKeys.PROCESSING_KEY, task_id)
            if not task_data:
                print(f"Warning: Task {task_id[:8]} not found in processing")
                return
                
            task = EmailTask(**json.loads(task_data))
            task.completed_at = time.time()
            task.result = result
            task.error = error
            task.status = ProcessingStates.COMPLETED if not error else ProcessingStates.FAILED
            
            # Remove from processing
            await self.redis_client.hdel(RedisKeys.PROCESSING_KEY, task_id)
            
            # Add to completed/failed
            if error:
                await self.redis_client.hset(RedisKeys.FAILED_KEY, task_id, json.dumps(task.dict()))
                await self.update_stats("failed_count", 1, increment=True)
            else:
                await self.redis_client.hset(RedisKeys.COMPLETED_KEY, task_id, json.dumps(task.dict()))
                await self.update_stats("completed_count", 1, increment=True)
            
            # Update stats
            processing_count = await self.redis_client.hlen(RedisKeys.PROCESSING_KEY)
            queue_size = await self.redis_client.llen(RedisKeys.QUEUE_KEY)
            await self.update_stats("currently_processing", processing_count)
            await self.update_stats("queue_size", queue_size)
            await self.update_stats("total_processed", 1, increment=True)
            
            status_emoji = "✅" if not error else "❌"
            print(f"{status_emoji} Completed task {task_id[:8]} - {'Success' if not error else f'Failed: {error}'}")
            
        except Exception as e:
            raise StorageError(f"Error completing task: {e}")
    
    async def cache_email_data(self, message_id: str, email_data: dict) -> None:
        """Cache email data for deduplication."""
        try:
            await self.redis_client.hset(RedisKeys.EMAIL_CACHE_KEY, message_id, json.dumps(email_data))
            # Set expiration for cache entries (24 hours)
            await self.redis_client.expire(f"{RedisKeys.EMAIL_CACHE_KEY}:{message_id}", 86400)
        except Exception as e:
            print(f"Error caching email data: {e}")
    
    async def get_cached_email_data(self, message_id: str) -> Optional[dict]:
        """Get cached email data."""
        try:
            data = await self.redis_client.hget(RedisKeys.EMAIL_CACHE_KEY, message_id)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Error getting cached email data: {e}")
            return None
    
    async def is_message_processed(self, message_id: str) -> bool:
        """Check if message has been processed."""
        try:
            return await self.redis_client.sismember(RedisKeys.PROCESSED_MESSAGES_KEY, message_id)
        except Exception as e:
            print(f"Error checking processed message: {e}")
            return False
    
    async def mark_message_processed(self, message_id: str) -> None:
        """Mark message as processed."""
        try:
            await self.redis_client.sadd(RedisKeys.PROCESSED_MESSAGES_KEY, message_id)
            # Set expiration for processed messages (7 days)
            await self.redis_client.expire(RedisKeys.PROCESSED_MESSAGES_KEY, 604800)
        except Exception as e:
            print(f"Error marking message as processed: {e}")
    
    async def get_processing_details(self) -> List[Dict[str, Any]]:
        """Get details of currently processing tasks."""
        try:
            processing_tasks = await self.redis_client.hgetall(RedisKeys.PROCESSING_KEY)
            processing_details = []
            
            for task_id, task_data in processing_tasks.items():
                try:
                    task = EmailTask(**json.loads(task_data))
                    processing_details.append({
                        "task_id": task_id,
                        "email_from": task.email_data.get("from_email", "unknown"),
                        "status": task.status,
                        "queue_time": task.started_at - task.created_at if task.started_at else time.time() - task.created_at,
                        "processing_time": time.time() - task.started_at if task.started_at else None,
                        "created_at": task.created_at,
                        "started_at": task.started_at
                    })
                except Exception as e:
                    print(f"Error parsing processing task: {e}")
            
            return processing_details
        except Exception as e:
            raise StorageError(f"Error getting processing details: {e}")
    
    async def clear_all_queues(self) -> None:
        """Clear all queues (for debugging)."""
        try:
            await self.redis_client.delete(RedisKeys.QUEUE_KEY)
            await self.redis_client.delete(RedisKeys.PROCESSING_KEY)
            await self.redis_client.delete(RedisKeys.COMPLETED_KEY)
            await self.redis_client.delete(RedisKeys.FAILED_KEY)
            
            # Reset stats
            stats = ProcessingStats()
            await self.redis_client.hset(RedisKeys.STATS_KEY, mapping=stats.dict())
        except Exception as e:
            raise StorageError(f"Error clearing queues: {e}")

# Global Redis manager instance
redis_manager = RedisManager()