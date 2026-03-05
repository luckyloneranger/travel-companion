"""Simple in-memory rate limiter for expensive endpoints."""

import time
from collections import defaultdict
from fastapi import HTTPException, Request


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


# Journey planning: 5 requests per 10 minutes per user
plan_limiter = RateLimiter(max_requests=5, window_seconds=600)

# Day plan generation: 10 requests per 10 minutes per user
day_plan_limiter = RateLimiter(max_requests=10, window_seconds=600)

# Chat editing: 30 requests per 10 minutes per user
chat_limiter = RateLimiter(max_requests=30, window_seconds=600)

# Tips generation: 30 requests per 10 minutes per user
tips_limiter = RateLimiter(max_requests=30, window_seconds=600)
