import pytest
import asyncio
from datetime import datetime, timedelta

from src.infrastructure.ai.rate_limiter import RateLimiter, RateLimitConfig


class TestRateLimitConfig:
    def test_defaults(self):
        config = RateLimitConfig()
        
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.tokens_per_minute == 100000
        assert config.concurrent_requests == 10

    def test_custom_config(self):
        config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=500,
            tokens_per_minute=50000,
            concurrent_requests=5,
        )
        
        assert config.requests_per_minute == 30
        assert config.concurrent_requests == 5


class TestRateLimiter:
    @pytest.fixture
    def limiter(self):
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            concurrent_requests=3,
        )
        return RateLimiter(config)

    @pytest.mark.asyncio
    async def test_acquire_and_release(self, limiter):
        await limiter.acquire()
        assert limiter.current_minute_usage == 1
        
        limiter.release()
        assert limiter.current_minute_usage == 1

    @pytest.mark.asyncio
    async def test_multiple_acquires(self, limiter):
        for i in range(3):
            await limiter.acquire()
        
        assert limiter.current_minute_usage == 3
        
        for _ in range(3):
            limiter.release()

    @pytest.mark.asyncio
    async def test_get_stats(self, limiter):
        await limiter.acquire()
        limiter.release()
        
        stats = limiter.get_stats()
        
        assert stats["requests_per_minute"] == 1
        assert stats["minute_limit"] == 10
        assert stats["hour_limit"] == 100
        assert stats["concurrent_limit"] == 3

    @pytest.mark.asyncio
    async def test_concurrent_limit(self, limiter):
        acquired = []
        
        for _ in range(3):
            await limiter.acquire()
            acquired.append(True)
        
        assert len(acquired) == 3
        
        for _ in range(3):
            limiter.release()

    def test_current_usage_empty(self, limiter):
        assert limiter.current_minute_usage == 0
        assert limiter.current_hour_usage == 0

    @pytest.mark.asyncio
    async def test_acquire_with_tokens(self, limiter):
        await limiter.acquire(estimated_tokens=1000)
        
        stats = limiter.get_stats()
        assert stats["tokens_per_minute"] == 1000
        
        limiter.release()
