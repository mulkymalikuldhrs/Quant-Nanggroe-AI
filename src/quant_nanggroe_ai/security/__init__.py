"""Security Package — Authentication, Key Vault, Audit Trail, and Credential Management.

Provides:
- Auth: API key and JWT authentication
- KeyVault: Secure secret storage and retrieval
- AuditLogger: Append-only audit trail (from quant_nanggroe)
- CredentialInference: Smart credential detection and management
- Scanner: Prompt-injection warning scanner for external content
"""

from quant_nanggroe_ai.security.scanner import scan_prompt_injection, with_security_warnings

# Lazy imports to avoid import errors from missing dependencies
def __getattr__(name: str):
    """Lazy import for security modules."""
    _lazy_imports = {
        "APIKeyAuth": ".auth",
        "JWTAuth": ".auth",
        "AuthResult": ".auth",
        "AuditLogger": ".audit",
        "CredentialInference": ".credential_inference",
        "KeyVault": ".keyvault",
    }
    if name in _lazy_imports:
        import importlib
        module = importlib.import_module(_lazy_imports[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Scanner
    "scan_prompt_injection",
    "with_security_warnings",
    # Lazy-loaded
    "APIKeyAuth",
    "JWTAuth",
    "AuthResult",
    "AuditLogger",
    "CredentialInference",
    "KeyVault",
]

