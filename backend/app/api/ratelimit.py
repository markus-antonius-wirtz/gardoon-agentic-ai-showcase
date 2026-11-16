"""Sliding-window IP rate limiter protecting public Gemini API quota."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class SlidingWindowRateLimiter:
    """In-memory per-IP sliding window limiter (1-hour window)."""

    def __init__(self, max_requests_per_hour: int = 15) -> None:
        self.max_requests = max_requests_per_hour
        self.window_seconds = 3600.0
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    @staticmethod
    def extract_client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip", "")
        if real_ip:
            return real_ip.strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def check_or_raise(self, request: Request) -> int:
        """Record request or raise HTTP 429 if quota exceeded. Returns remaining quota."""
        ip = self.extract_client_ip(request)
        if ip in ("127.0.0.1", "::1", "testclient"):
            return self.max_requests

        now = time.monotonic()
        dq = self._buckets[ip]
        cutoff = now - self.window_seconds
        while dq and dq[0] < cutoff:
            dq.popleft()

        if len(dq) >= self.max_requests:
            retry_after = int(max(1.0, self.window_seconds - (now - dq[0])))
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Public showcase rate limit reached ({self.max_requests} live agent runs/hour per IP). "
                    f"Retry in ~{retry_after // 60 + 1} min or explore the pre-configured scenarios."
                ),
            )

        dq.append(now)
        return max(0, self.max_requests - len(dq))
