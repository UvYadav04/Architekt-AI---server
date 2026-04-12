import redis.asyncio as redis
import uuid
import time
from typing import Optional, Dict


class RedisSessionStore:
    _instance = None

    def __new__(cls, redis_url: str = "redis://localhost:6379"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__(redis_url)
        return cls._instance

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(
            redis_url, decode_responses=True, max_connections=20  # connection pool
        )

    async def create_session(self, user_id: Optional[str] = None, ttl: int = 3600):
        session_id = str(uuid.uuid4())
        key = f"session:{session_id}"

        data = {
            "user_id": user_id or "",
            "request_count": 0,
            "created_at": int(time.time()),
        }

        await self.redis.hset(key, mapping=data)
        await self.redis.expire(key, ttl)

        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict]:
        key = f"session:{session_id}"
        data = await self.redis.hgetall(key)
        return data if data else None

    async def update_session(self, session_id: str, updates: Dict):
        key = f"session:{session_id}"
        await self.redis.hset(key, mapping=updates)

    async def delete_session(self, session_id: str):
        key = f"session:{session_id}"
        await self.redis.delete(key)

    async def increment_requests(self, session_id: str):
        key = f"session:{session_id}"
        return await self.redis.hincrby(key, "request_count", 1)

    async def track_request(self, session_id: str):
        key = f"session:{session_id}:requests"
        now = time.time()

        await self.redis.zadd(key, {str(now): now})
        await self.redis.zremrangebyscore(key, 0, now - 60)
        await self.redis.expire(key, 120)

    async def get_last_minute_requests(self, session_id: str) -> int:
        key = f"session:{session_id}:requests"
        now = time.time()
        return await self.redis.zcount(key, now - 60, now)

    async def is_rate_limited(self, session_id: str, limit: int = 60):
        count = await self.get_last_minute_requests(session_id)
        return count >= limit

    async def increment_active(self, route_type: str):
        key = f"active:{route_type}"
        return await self.redis.incr(key)

    async def decrement_active(self, route_type: str):
        key = f"active:{route_type}"
        val = await self.redis.decr(key)

        # safety: avoid negative
        if val < 0:
            await self.redis.set(key, 0)

    async def get_active(self, route_type: str):
        key = f"active:{route_type}"
        val = await self.redis.get(key)
        return int(val) if val else 0

    async def enqueue(self, queue_name: str, job: str):
        await self.redis.lpush(queue_name, job)

    async def dequeue(self, queue_name: str):
        return await self.redis.brpop(queue_name)

    async def get_queue_length(self, queue_name: str):
        return await self.redis.llen(queue_name)
