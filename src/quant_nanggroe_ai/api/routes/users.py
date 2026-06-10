"""
User API Routes for Quant-Nanggroe-AI
Adapted from ai-manus feat/user branch.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from quant_nanggroe_ai.api.user_service import (
    UserCreate, UserLogin, UserUpdate, UserResponse, TokenResponse, UserService,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])

# Singleton service instance
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, svc: UserService = Depends(get_user_service)):
    """Register a new user account."""
    try:
        return await svc.create_user(user_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, svc: UserService = Depends(get_user_service)):
    """Authenticate and get access tokens."""
    try:
        return await svc.authenticate(login_data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, svc: UserService = Depends(get_user_service)):
    """Refresh access token."""
    try:
        return await svc.refresh_access(refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user(user_id: str, svc: UserService = Depends(get_user_service)):
    """Get current user profile."""
    user = await svc.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_id: str,
    update: UserUpdate,
    svc: UserService = Depends(get_user_service),
):
    """Update current user profile."""
    result = await svc.update_user(user_id, update)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_account(user_id: str, svc: UserService = Depends(get_user_service)):
    """Deactivate current user account."""
    success = await svc.deactivate_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
