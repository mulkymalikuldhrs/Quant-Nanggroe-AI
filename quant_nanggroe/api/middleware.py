"""API Middleware — Auth, security headers, rate limiting
======================================================="""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from quant_nanggroe.security.auth import APIKeyAuth, JWTAuth, UserRole

logger = logging.getLogger(__name__)


# ── Auth Middleware ─────────────────────────────────────────────────────────


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT + API key authentication middleware.

    Validates the ``Authorization`` header on every request to protected
    route prefixes.  Public endpoints (``/health``, ``/metrics``,
    ``/docs``, ``/openapi.json``) are bypassed.

    Accepts:
    - ``Authorization: Bearer <jwt_token>``  (JWT)
    - ``Authorization: ApiKey <api_key>``    (API key)

    On success, adds ``request.state.user_id`` and ``request.state.user_role``.
    On failure, returns **401 Unauthorized**.
    """

    def __init__(self, app: Any, auth: Optional[JWTAuth] = None,
                 api_key_auth: Optional[APIKeyAuth] = None,
                 exclude_paths: Optional[set[str]] = None) -> None:
        super().__init__(app)
        # ponytail: single source of truth = injected auth (built from settings
        # in app.py, which fail-closes on the unset sentinel). Never re-read env
        # here — that created a second secret path divergent from app.py.
        if auth is None:
            secret = os.environ.get("QNAI_JWT_SECRET", "")
            if not secret:
                raise RuntimeError(
                    "AuthMiddleware constructed without auth and QNAI_JWT_SECRET unset. "
                    "Refusing to run with an ephemeral key (fail-closed)."
                )
            auth = JWTAuth(secret_key=secret)
        self._jwt = auth
        self._apikey = api_key_auth or APIKeyAuth()
        self._exclude_paths = exclude_paths or {"/health", "/metrics", "/docs",
                                                "/openapi.json", "/favicon.ico"}
        # ponytail: fail-closed — dev mode only with explicit opt-in, never silent
        self._insecure_optin = os.environ.get("QNAI_ALLOW_INSECURE_DEV", "").lower() in ("1", "true", "yes")
        self._dev_mode = (not bool(os.environ.get("QNAI_API_KEY", ""))) and self._insecure_optin
        if self._dev_mode:
            logger.warning("Auth BYPASSED — QNAI_ALLOW_INSECURE_DEV=true and no QNAI_API_KEY set")
        elif not os.environ.get("QNAI_API_KEY", ""):
            logger.warning("No QNAI_API_KEY set; auth ENFORCED (all /api/* require token). Set QNAI_ALLOW_INSECURE_DEV=true to disable (dev only).")

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path

        # Dev mode: skip auth entirely
        if self._dev_mode:
            return await call_next(request)

        # Bypass auth for public endpoints
        if path in self._exclude_paths or path.startswith(("/docs", "/redoc", "/openapi.json")):
            return await call_next(request)

        # Bypass auth for static files (dashboard UI)
        if not path.startswith("/api/"):
            return await call_next(request)

        # ponytail: lo bilang "ini mesin uang, jangan pakai auth". Localhost bypass.
        # FIX S1: Gate behind env var to prevent unauthenticated admin access in production.
        client = request.client
        if client and client.host in ("127.0.0.1", "::1", "localhost"):
            if os.environ.get("QNAI_ALLOW_LOCALHOST_BYPASS", "0") == "1":
                request.state.user_id = "local"
                request.state.user_role = UserRole.ADMIN
                return await call_next(request)
            # else: fall through to normal auth

        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return Response(
                content='{"detail":"Missing Authorization header"}',
                status_code=401, media_type="application/json",
            )

        try:
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                payload = self._jwt.validate_token(token)
                request.state.user_id = payload.user_id
                request.state.user_role = payload.role
            elif auth_header.startswith("ApiKey "):
                api_key = auth_header[7:]
                result = self._apikey.authenticate(api_key)
                if not result.success:
                    raise ValueError(result.error or "Invalid API key")
                request.state.user_id = result.user_id
                request.state.user_role = result.role or UserRole.VIEWER
            else:
                return Response(
                    content='{"detail":"Unsupported auth scheme (use Bearer or ApiKey)"}',
                    status_code=401, media_type="application/json",
                )
        except ValueError as e:
            return Response(
                content=f'{{"detail":"{str(e)}"}}',
                status_code=401, media_type="application/json",
            )

        response = await call_next(request)
        return response


# ── Security Headers Middleware ──────────────────────────────────────────────


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security HTTP headers to every response.

    Headers applied:
    - ``Strict-Transport-Security`` (HSTS, 1 year)
    - ``X-Content-Type-Options: nosniff``
    - ``X-Frame-Options: DENY``
    - ``X-XSS-Protection: 1; mode=block``
    - ``Referrer-Policy: strict-origin-when-cross-origin``
    - ``Permissions-Policy`` (restrict geolocation, camera, microphone)
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), usb=()"
        )
        return response


# ── Rate Limiting ───────────────────────────────────────────────────────────


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware.

    Tracks requests per client IP address and enforces a maximum
    number of requests per minute. Uses an in-memory sliding window.
    """

    def __init__(self, app: Any, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = {}
        self._request_count: int = 0

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        client_id = request.client.host if request.client else "unknown"
        now = time.time()

        self._request_count += 1
        # Prune stale entries every 100 requests to prevent memory leak
        if self._request_count % 100 == 0:
            self.requests = {
                ip: [t for t in timestamps if now - t < 60]
                for ip, timestamps in self.requests.items()
                if timestamps and any(now - t < 60 for t in timestamps)
            }

        if client_id not in self.requests:
            self.requests[client_id] = []

        self.requests[client_id] = [t for t in self.requests[client_id] if now - t < 60]

        if len(self.requests[client_id]) >= self.requests_per_minute:
            return Response(content='{"detail":"Rate limit exceeded"}',
                            status_code=429, media_type="application/json")

        self.requests[client_id].append(now)
        response = await call_next(request)
        return response


# ── Request ID Middleware ────────────────────────────────────────────────────


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request/response.

    If the client supplies ``X-Request-ID``, it is reused; otherwise a
    12-character UUID is generated.  The ID is set on ``request.state``
    and echoed in the response header.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:12]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
