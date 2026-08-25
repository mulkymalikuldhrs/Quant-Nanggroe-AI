"""Auth API routes — JWT issuance for WebSocket clients.

POST /api/auth/token sits behind AuthMiddleware (ApiKey/Bearer), so a
dashboard client authenticates with its API key and receives a
short-lived JWT accepted as ``?token=`` by /api/ws/stream.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from quant_nanggroe.security.auth import JWTAuth, UserRole

router = APIRouter()


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_at: float


@router.post("/auth/token", response_model=TokenResponse)
async def issue_token(request: Request) -> TokenResponse:
    """Issue a short-lived JWT for WS auth (requires ApiKey/Bearer auth)."""
    jwt_auth = getattr(request.app.state, "auth", None)
    if not isinstance(jwt_auth, JWTAuth):
        raise HTTPException(status_code=503, detail="JWT auth not configured")

    user_id = str(getattr(request.state, "user_id", "") or "admin")
    role = getattr(request.state, "user_role", None)
    if not isinstance(role, UserRole):
        role = UserRole.ADMIN

    token = jwt_auth.create_token(user_id=user_id, role=role)
    expires_at = jwt_auth.validate_token(token).expires_at
    return TokenResponse(token=token, expires_at=expires_at)
