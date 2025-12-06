import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from typing import Deque


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    tokens_per_minute: int = 100000
    concurrent_requests: int = 10


class RateLimiter:
    def __init__(self, config: RateLimitConfig | None = None):
        self._config = config or RateLimitConfig()
        self._minute_requests: Deque[datetime] = deque()
        self._hour_requests: Deque[datetime] = deque()
        self._minute_tokens: Deque[tuple[datetime, int]] = deque()
        self._semaphore = asyncio.Semaphore(self._config.concurrent_requests)
        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 0) -> None:
        await self._semaphore.acquire()
        try:
            async with self._lock:
                await self._wait_for_rate_limit(estimated_tokens)
                now = datetime.utcnow()
                self._minute_requests.append(now)
                self._hour_requests.append(now)
                if estimated_tokens > 0:
                    self._minute_tokens.append((now, estimated_tokens))
        except Exception:
            self._semaphore.release()
            raise

    def release(self) -> None:
        self._semaphore.release()

    async def _wait_for_rate_limit(self, estimated_tokens: int) -> None:
        now = datetime.utcnow()
        self._cleanup_old_requests(now)

        while True:
            minute_count = len(self._minute_requests)
            hour_count = len(self._hour_requests)
            minute_token_count = sum(t[1] for t in self._minute_tokens)

            if minute_count >= self._config.requests_per_minute:
                oldest = self._minute_requests[0]
                wait_time = (oldest + timedelta(minutes=1) - now).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time + 0.1)
                    now = datetime.utcnow()
                    self._cleanup_old_requests(now)
                    continue

            if hour_count >= self._config.requests_per_hour:
                oldest = self._hour_requests[0]
                wait_time = (oldest + timedelta(hours=1) - now).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(min(wait_time + 0.1, 60))
                    now = datetime.utcnow()
                    self._cleanup_old_requests(now)
                    continue

            if minute_token_count + estimated_tokens > self._config.tokens_per_minute:
                if self._minute_tokens:
                    oldest = self._minute_tokens[0][0]
                    wait_time = (oldest + timedelta(minutes=1) - now).total_seconds()
                    if wait_time > 0:
                        await asyncio.sleep(wait_time + 0.1)
                        now = datetime.utcnow()
                        self._cleanup_old_requests(now)
                        continue

            break

    def _cleanup_old_requests(self, now: datetime) -> None:
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        while self._minute_requests and self._minute_requests[0] < minute_ago:
            self._minute_requests.popleft()

        while self._hour_requests and self._hour_requests[0] < hour_ago:
            self._hour_requests.popleft()

        while self._minute_tokens and self._minute_tokens[0][0] < minute_ago:
            self._minute_tokens.popleft()

    @property
    def current_minute_usage(self) -> int:
        self._cleanup_old_requests(datetime.utcnow())
        return len(self._minute_requests)

    @property
    def current_hour_usage(self) -> int:
        self._cleanup_old_requests(datetime.utcnow())
        return len(self._hour_requests)

    def get_stats(self) -> dict:
        now = datetime.utcnow()
        self._cleanup_old_requests(now)
        return {
            "requests_per_minute": len(self._minute_requests),
            "requests_per_hour": len(self._hour_requests),
            "tokens_per_minute": sum(t[1] for t in self._minute_tokens),
            "concurrent_limit": self._config.concurrent_requests,
            "minute_limit": self._config.requests_per_minute,
            "hour_limit": self._config.requests_per_hour,
        }
