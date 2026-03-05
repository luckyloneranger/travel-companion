"""Simple in-memory rate limiter for expensive endpoints."""

import time
from collections import defaultdict
from functools import lru_cache

from fastapi import HTTPException


class RateLimiter:
    """Per-user rate limiter using a sliding window counter."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, user_id: str) -> None:
        """Raise 429 if user exceeds rate limit."""
        now = time.monotonic()
        window_start = now - self.window_seconds

        # Clean old entries
        self._requests[user_id] = [
            t for t in self._requests[user_id] if t > window_start
        ]

        if len(self._requests[user_id]) >= self.max_requests:
            raise HTTPException(
                429,
                f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds // 60} minutes.",
            )

        self._requests[user_id].append(now)


@lru_cache
def _get_limiters():
    """Create rate limiters from settings (lazy, cached)."""
    from app.config.settings import get_settings
    s = get_settings()
    return {
        "plan": RateLimiter(s.rate_limit_plan_requests, s.rate_limit_plan_window_seconds),
        "day_plan": RateLimiter(s.rate_limit_day_plan_requests, s.rate_limit_day_plan_window_seconds),
        "chat": RateLimiter(s.rate_limit_chat_requests, s.rate_limit_chat_window_seconds),
        "tips": RateLimiter(s.rate_limit_tips_requests, s.rate_limit_tips_window_seconds),
    }


def get_plan_limiter() -> RateLimiter:
    return _get_limiters()["plan"]


def get_day_plan_limiter() -> RateLimiter:
    return _get_limiters()["day_plan"]


def get_chat_limiter() -> RateLimiter:
    return _get_limiters()["chat"]


def get_tips_limiter() -> RateLimiter:
    return _get_limiters()["tips"]
