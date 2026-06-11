"""Tests for Security module — auth, keyvault, credential inference, audit."""

import os
import tempfile

import pytest


class TestAPIKeyAuth:
    """Tests for APIKeyAuth."""

    def test_import(self):
        from quant_nanggroe_ai.security.auth import APIKeyAuth
        assert APIKeyAuth is not None

    def test_creation(self):
        from quant_nanggroe_ai.security.auth import APIKeyAuth
        auth = APIKeyAuth()
        assert auth is not None


class TestJWTAuth:
    """Tests for JWTAuth."""

    def test_import(self):
        from quant_nanggroe_ai.security.auth import JWTAuth
        assert JWTAuth is not None


class TestCredentialInference:
    """Tests for CredentialInference."""

    def test_import(self):
        from quant_nanggroe_ai.security.credential_inference import CredentialInference
        assert CredentialInference is not None

    def test_creation(self):
        from quant_nanggroe_ai.security.credential_inference import CredentialInference
        ci = CredentialInference()
        assert ci is not None


class TestKeyVault:
    """Tests for KeyVault."""

    def test_import(self):
        from quant_nanggroe_ai.security.keyvault import KeyVault
        assert KeyVault is not None

    def test_creation(self):
        from quant_nanggroe_ai.security.keyvault import KeyVault
        kv = KeyVault()
        assert kv is not None


class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_import(self):
        from quant_nanggroe_ai.security.audit import AuditLogger
        assert AuditLogger is not None

    def test_creation(self):
        from quant_nanggroe_ai.security.audit import AuditLogger
        logger = AuditLogger()
        assert logger is not None


class TestSecurityInit:
    """Tests for security package __init__."""

    def test_package_import(self):
        import quant_nanggroe_ai.security
        assert quant_nanggroe_ai.security is not None
