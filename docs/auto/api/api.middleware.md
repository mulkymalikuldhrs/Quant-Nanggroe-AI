# api.middleware

## Class: 

JWT + API key authentication middleware.

Validates the ``Authorization`` header on every request to protected
route prefixes.  Public endpoints (``/health``, ``/metrics``,
``/docs``, ``/openapi.json``) are bypassed.

Accepts:
- ``Authorization: Bearer <jwt_token>``  (JWT)
- ``Authorization: ApiKey <api_key>``    (API key)

On success, adds ``request.state.user_id`` and ``request.state.user_role``.
On failure, returns **401 Unauthorized**.

**Methods:** __init__

*Line: 21*

---

## Class: 

Add security HTTP headers to every response.

Headers applied:
- ``Strict-Transport-Security`` (HSTS, 1 year)
- ``X-Content-Type-Options: nosniff``
- ``X-Frame-Options: DENY``
- ``X-XSS-Protection: 1; mode=block``
- ``Referrer-Policy: strict-origin-when-cross-origin``
- ``Permissions-Policy`` (restrict geolocation, camera, microphone)

*Line: 90*

---

## Class: 

Simple rate limiting middleware.

Tracks requests per client IP address and enforces a maximum
number of requests per minute. Uses an in-memory sliding window.

**Methods:** __init__

*Line: 118*

---

## Function: 

*Line: 36*

---

## Function: 

*Line: 125*

---

