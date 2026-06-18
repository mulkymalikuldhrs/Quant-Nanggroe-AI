"""API Middleware — Auth, CORS, rate limiting
=========================================="""

from __future__ import annotations

import time
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware.

    Tracks requests per client IP address and enforces a maximum
    number of requests per minute. Uses an in-memory sliding window.
    """

    def __init__(self, app: Any, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process request with rate limiting check.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in the chain.

        Returns:
            HTTP response or 429 if rate limit exceeded.
        """
        client_id = request.client.host if request.client else "unknown"
        now = time.time()

        if client_id not in self.requests:
            self.requests[client_id] = []

        # Clean old requests
        self.requests[client_id] = [t for t in self.requests[client_id] if now - t < 60]

        if len(self.requests[client_id]) >= self.requests_per_minute:
            return Response(content="Rate limit exceeded", status_code=429)

        self.requests[client_id].append(now)
        response = await call_next(request)
        return response
