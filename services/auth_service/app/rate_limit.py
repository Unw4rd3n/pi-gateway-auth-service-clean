from redis.asyncio import Redis


class RateLimitExceeded(Exception):
    pass


class RedisRateLimiter:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def enforce(self, key: str, limit: int, window_seconds: int) -> None:
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, window_seconds)
        if current > limit:
            raise RateLimitExceeded(f"Rate limit exceeded for key={key}")
