"""Security and Authentication Framework.

Provides secure secrets management, API authentication, audit logging,
and smart credential detection for the Quant Nanggroe AI system.

Modules
-------
keyvault
    Secure secrets management via environment variables.
auth
    API key and JWT token authentication with role-based access.
audit
    Append-only audit trail with SQLite storage.
credential_inference
    Smart credential detection and validation.

Usage
-----
    from quant_nanggroe.security import KeyVault, JWTAuth, AuditLogger

    # Secure secrets
    vault = KeyVault()
    api_key = vault.get_secret("ALPACA_API_KEY")

    # Authentication
    auth = JWTAuth(secret_key="...")
    token = auth.create_token(user_id="trader1", role="trader")

    # Audit logging
    audit = AuditLogger(db_path="audit.db")
    await audit.log_event(
        agent="risk_agent",
        event_type="risk_check",
        symbol="BTC/USDT",
        verdict="approved",
    )
"""

from quant_nanggroe.security.audit import AuditLogger, AuditRecord
from quant_nanggroe.security.auth import APIKeyAuth, JWTAuth, UserRole
from quant_nanggroe.security.credential_inference import (
    CredentialCheck,
    CredentialInference,
    ExchangeType,
)
from quant_nanggroe.security.keyvault import KeyVault

__all__ = [
    # Key Vault
    "KeyVault",
    # Auth
    "APIKeyAuth",
    "JWTAuth",
    "UserRole",
    # Audit
    "AuditLogger",
    "AuditRecord",
    # Credential Inference
    "CredentialInference",
    "CredentialCheck",
    "ExchangeType",
]
