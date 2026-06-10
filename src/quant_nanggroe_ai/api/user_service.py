"""
User Management Service for Quant-Nanggroe-AI
Adapted from ai-manus feat/user branch for PostgreSQL-backed user management.
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Models ──────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Schema for user registration."""
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = "trader"  # admin/trader/viewer


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class UserUpdate(BaseModel):
    """Schema for user profile update."""
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    role: Optional[str] = None  # admin only


class UserResponse(BaseModel):
    """Schema for user API response."""
    id: str
    username: str
    email: str
    role: str
    display_name: Optional[str] = None
    is_active: bool = True
    created_at: str = ""
    last_login: Optional[str] = None


class TokenResponse(BaseModel):
    """Schema for auth token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


# ── Password Hashing ────────────────────────────────────────────

class PasswordHasher:
    """PBKDF2-SHA256 password hashing (OWASP recommended)."""

    ITERATIONS = 100_000
    SALT_LEN = 32
    HASH_LEN = 32

    @classmethod
    def hash(cls, password: str) -> str:
        salt = secrets.token_bytes(cls.SALT_LEN)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            cls.ITERATIONS,
            dklen=cls.HASH_LEN,
        )
        return f"pbkdf2:sha256:{cls.ITERATIONS}${salt.hex()}${dk.hex()}"

    @classmethod
    def verify(cls, password: str, stored_hash: str) -> bool:
        try:
            parts = stored_hash.split("$")
            if len(parts) != 3:
                return False
            header, salt_hex, _ = parts
            _, _, iterations_str = header.split(":")
            iterations = int(iterations_str)
            salt = bytes.fromhex(salt_hex)
            dk = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                iterations,
                dklen=cls.HASH_LEN,
            )
            expected = bytes.fromhex(stored_hash.split("$")[2])
            return secrets.compare_digest(dk, expected)
        except (ValueError, IndexError):
            return False


# ── User Service ────────────────────────────────────────────────

class UserService:
    """
    PostgreSQL-backed user management service.
    Supports registration, login, JWT token management, and role-based access.
    """

    def __init__(self, db_pool=None):
        """
        Args:
            db_pool: AsyncPG or psycopg connection pool.
                     If None, uses in-memory storage for development.
        """
        self.db = db_pool
        self._memory_store: dict[str, dict[str, Any]] = {}
        self._refresh_tokens: dict[str, dict[str, Any]] = {}
        self._hasher = PasswordHasher()

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Register a new user."""
        # Check if username/email already exists
        if await self._get_user_by_username(user_data.username):
            raise ValueError(f"Username '{user_data.username}' already exists")
        if await self._get_user_by_email(user_data.email):
            raise ValueError(f"Email '{user_data.email}' already registered")

        user_id = f"usr_{secrets.token_hex(12)}"
        password_hash = self._hasher.hash(user_data.password)
        now = datetime.utcnow().isoformat()

        user_record = {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash,
            "role": user_data.role,
            "display_name": None,
            "is_active": True,
            "created_at": now,
            "last_login": None,
        }

        if self.db:
            await self.db.execute(
                """
                INSERT INTO users (id, username, email, password_hash, role, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user_id, user_data.username, user_data.email,
                password_hash, user_data.role, True, now,
            )
        else:
            self._memory_store[user_id] = user_record

        return UserResponse(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            role=user_data.role,
            created_at=now,
        )

    async def authenticate(self, login_data: UserLogin) -> TokenResponse:
        """Authenticate user and return JWT tokens."""
        user = await self._get_user_by_username(login_data.username)
        if not user:
            raise ValueError("Invalid credentials")

        if not self._hasher.verify(login_data.password, user["password_hash"]):
            raise ValueError("Invalid credentials")

        if not user.get("is_active", True):
            raise ValueError("Account is deactivated")

        # Generate tokens
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(48)

        # Store refresh token
        self._refresh_tokens[refresh_token] = {
            "user_id": user["id"],
            "created_at": time.time(),
            "expires_at": time.time() + 86400 * 30,  # 30 days
        }

        # Update last login
        now = datetime.utcnow().isoformat()
        if self.db:
            await self.db.execute(
                "UPDATE users SET last_login=$1 WHERE id=$2",
                now, user["id"],
            )
        else:
            user["last_login"] = now

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
        )

    async def refresh_access(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        token_data = self._refresh_tokens.get(refresh_token)
        if not token_data:
            raise ValueError("Invalid refresh token")

        if time.time() > token_data["expires_at"]:
            del self._refresh_tokens[refresh_token]
            raise ValueError("Refresh token expired")

        user = await self._get_user_by_id(token_data["user_id"])
        if not user or not user.get("is_active", True):
            raise ValueError("User not found or deactivated")

        # Rotate tokens
        new_access = secrets.token_urlsafe(32)
        new_refresh = secrets.token_urlsafe(48)

        del self._refresh_tokens[refresh_token]
        self._refresh_tokens[new_refresh] = {
            "user_id": user["id"],
            "created_at": time.time(),
            "expires_at": time.time() + 86400 * 30,
        }

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=3600,
        )

    async def get_user(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID."""
        user = await self._get_user_by_id(user_id)
        if not user:
            return None
        return self._to_response(user)

    async def update_user(self, user_id: str, update: UserUpdate) -> Optional[UserResponse]:
        """Update user profile."""
        user = await self._get_user_by_id(user_id)
        if not user:
            return None

        if update.email:
            user["email"] = update.email
        if update.display_name:
            user["display_name"] = update.display_name

        if self.db:
            sets = []
            values = []
            if update.email:
                sets.append("email = $1")
                values.append(update.email)
            if update.display_name:
                sets.append("display_name = $2")
                values.append(update.display_name)
            if sets:
                values.append(user_id)
                await self.db.execute(
                    f"UPDATE users SET {', '.join(sets)} WHERE id = ${len(values)}",
                    *values,
                )
        else:
            self._memory_store[user_id] = user

        return self._to_response(user)

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        user = await self._get_user_by_id(user_id)
        if not user:
            return False
        user["is_active"] = False
        if self.db:
            await self.db.execute(
                "UPDATE users SET is_active = FALSE WHERE id = $1",
                user_id,
            )
        return True

    # ── Internal ──────────────────────────────────────────────

    async def _get_user_by_id(self, user_id: str) -> Optional[dict]:
        if self.db:
            row = await self.db.fetchrow(
                "SELECT * FROM users WHERE id = $1", user_id
            )
            return dict(row) if row else None
        return self._memory_store.get(user_id)

    async def _get_user_by_username(self, username: str) -> Optional[dict]:
        if self.db:
            row = await self.db.fetchrow(
                "SELECT * FROM users WHERE username = $1", username
            )
            return dict(row) if row else None
        for user in self._memory_store.values():
            if user["username"] == username:
                return user
        return None

    async def _get_user_by_email(self, email: str) -> Optional[dict]:
        if self.db:
            row = await self.db.fetchrow(
                "SELECT * FROM users WHERE email = $1", email
            )
            return dict(row) if row else None
        for user in self._memory_store.values():
            if user["email"] == email:
                return user
        return None

    def _to_response(self, user: dict) -> UserResponse:
        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user.get("role", "trader"),
            display_name=user.get("display_name"),
            is_active=user.get("is_active", True),
            created_at=user.get("created_at", ""),
            last_login=user.get("last_login"),
        )
