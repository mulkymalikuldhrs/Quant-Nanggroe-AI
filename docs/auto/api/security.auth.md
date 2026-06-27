# security.auth

## Class: 

User role with hierarchical access levels.

Attributes
----------
ADMIN:
    Full system access — can manage users, system config, and all operations.
TRADER:
    Trading operations — can place/cancel orders and view positions.
ANALYST:
    Analysis access — can run analysis and view data, but not trade.
VIEWER:
    Read-only — can view data and reports only.

*Line: 42*

---

## Class: 

JWT token payload data.

Attributes
----------
user_id:
    Unique user identifier.
role:
    User's role.
issued_at:
    Token issue time (Unix timestamp).
expires_at:
    Token expiration time (Unix timestamp).
jti:
    JWT ID (unique token identifier for revocation).

*Line: 84*

---

## Class: 

Result of an authentication attempt.

Attributes
----------
success:
    Whether authentication succeeded.
user_id:
    Authenticated user ID (if successful).
role:
    Authenticated user's role (if successful).
error:
    Error message (if failed).
token:
    JWT token string (if successful, for JWT auth).

*Line: 110*

---

## Class: 

API key-based authentication.

Validates API keys against a configurable store, mapping each key
to a user ID and role.

Parameters
----------
api_keys:
    Mapping of API key → ``{"user_id": str, "role": UserRole}``.

Examples
--------
.. code-block:: python

    auth = APIKeyAuth(
        api_keys={
            "ak-test-admin-001": {"user_id": "admin1", "role": UserRole.ADMIN},
            "ak-test-trader-001": {"user_id": "trader1", "role": UserRole.TRADER},
        }
    )
    result = auth.authenticate("ak-test-admin-001")
    assert result.success

**Methods:** __init__, add_key, remove_key, authenticate, has_permission, key_count

*Line: 140*

---

## Class: 

JWT token-based authentication with role-based access control.

Uses HMAC-SHA256 for token signing. Tokens contain user ID, role,
and expiration claims.

Parameters
----------
secret_key:
    HMAC secret key for signing tokens. **Must be kept secure.**
default_ttl:
    Default token time-to-live in seconds (default: 3600 = 1 hour).
algorithm:
    Signing algorithm (default: ``"HS256"``).

Examples
--------
.. code-block:: python

    auth = JWTAuth(secret_key="my-secret-key")
    token = auth.create_token(user_id="trader1", role=UserRole.TRADER)
    payload = auth.validate_token(token)
    assert payload.user_id == "trader1"

**Methods:** __init__, create_token, validate_token, refresh_token, revoke_token, has_permission, role_has_permission, is_role_at_least, _sign, __repr__

*Line: 251*

---

## Function: 

*Line: 165*

---

## Function: 

Register an API key.

Parameters
----------
api_key:
    The API key string.
user_id:
    User ID associated with this key.
role:
    Role assigned to this key.

*Line: 171*

---

## Function: 

Remove an API key.

Parameters
----------
api_key:
    The API key to remove.

*Line: 185*

---

## Function: 

Authenticate using an API key.

Parameters
----------
api_key:
    The API key to validate.

Returns
-------
AuthResult
    Authentication result with user info.

*Line: 195*

---

## Function: 

Check if an API key has permission for an action.

Parameters
----------
api_key:
    The API key to check.
action:
    The action to verify (``"read"``, ``"trade"``, ``"admin"``).

Returns
-------
bool

*Line: 221*

---

## Function: 

Number of registered API keys.

*Line: 242*

---

## Function: 

*Line: 276*

---

## Function: 

Create a new JWT token.

Parameters
----------
user_id:
    User ID to encode in the token.
role:
    User's role.
ttl:
    Token time-to-live in seconds. Uses ``default_ttl`` if ``None``.

Returns
-------
str
    Encoded JWT token string.

*Line: 287*

---

## Function: 

Validate a JWT token and return the payload.

Parameters
----------
token:
    JWT token string.

Returns
-------
TokenPayload
    Decoded and validated token payload.

Raises
------
ValueError
    If the token is invalid, expired, or revoked.

*Line: 330*

---

## Function: 

Refresh an existing token, creating a new one with updated expiration.

Parameters
----------
token:
    Current valid JWT token.
ttl:
    New token TTL in seconds. Uses ``default_ttl`` if ``None``.

Returns
-------
str
    New JWT token string.

Raises
------
ValueError
    If the current token is invalid.

*Line: 382*

---

## Function: 

Revoke a token by its JWT ID.

Parameters
----------
token:
    JWT token to revoke.

*Line: 412*

---

## Function: 

Check if a token's role has permission for an action.

Parameters
----------
token:
    JWT token string.
action:
    Action to check.

Returns
-------
bool

*Line: 427*

---

## Function: 

Check if a role has permission for an action (no token required).

Parameters
----------
role:
    User role.
action:
    Action to check.

Returns
-------
bool

*Line: 449*

---

## Function: 

Check if a role meets or exceeds a minimum level.

Parameters
----------
role:
    The role to check.
minimum:
    The minimum required role.

Returns
-------
bool

*Line: 467*

---

## Function: 

Sign data using HMAC-SHA256.

Parameters
----------
data:
    String data to sign.

Returns
-------
bytes
    HMAC signature.

*Line: 485*

---

## Function: 

*Line: 504*

---

