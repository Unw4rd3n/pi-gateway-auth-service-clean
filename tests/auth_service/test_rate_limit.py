import pytest

from services.auth_service.app.rate_limit import RateLimitExceeded, RedisRateLimiter


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def incr(self, key: str):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, _seconds: int):
        return True


@pytest.mark.asyncio
async def test_rate_limit_allows_requests_until_limit():
    limiter = RedisRateLimiter(FakeRedis())

    await limiter.enforce("login:127.0.0.1", limit=2, window_seconds=60)
    await limiter.enforce("login:127.0.0.1", limit=2, window_seconds=60)


@pytest.mark.asyncio
async def test_rate_limit_raises_after_limit():
    limiter = RedisRateLimiter(FakeRedis())

    await limiter.enforce("login:127.0.0.1", limit=1, window_seconds=60)

    with pytest.raises(RateLimitExceeded):
        await limiter.enforce("login:127.0.0.1", limit=1, window_seconds=60)
