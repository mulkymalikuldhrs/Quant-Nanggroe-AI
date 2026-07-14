#!/usr/bin/env python3
"""Tests: CredentialInference — exchange detection, credential validation.

All tests are deterministic — no network calls or external dependencies.
"""

from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from quant_nanggroe.security.credential_inference import (
    CredentialInference,
    CredentialCheck,
    ExchangeType,
    _EXCHANGE_KEY_PATTERNS,
)


class TestExchangeType(unittest.TestCase):
    def test_values(self):
        self.assertEqual(ExchangeType.ALPACA.value, "alpaca")
        self.assertEqual(ExchangeType.BINANCE.value, "binance")
        self.assertEqual(ExchangeType.COINBASE.value, "coinbase")
        self.assertEqual(ExchangeType.OKX.value, "okx")
        self.assertEqual(ExchangeType.BYBIT.value, "bybit")
        self.assertEqual(ExchangeType.KRAKEN.value, "kraken")
        self.assertEqual(ExchangeType.SOLANA.value, "solana")
        self.assertEqual(ExchangeType.UNKNOWN.value, "unknown")


class TestCredentialCheck(unittest.TestCase):
    def test_default_construction(self):
        cc = CredentialCheck()
        self.assertEqual(cc.exchange_type, ExchangeType.UNKNOWN)
        self.assertFalse(cc.is_complete)
        self.assertIsNone(cc.is_valid)
        self.assertEqual(cc.missing_fields, [])
        self.assertEqual(cc.warnings, [])

    def test_custom_construction(self):
        cc = CredentialCheck(
            exchange_type=ExchangeType.ALPACA,
            is_complete=True,
            is_valid=True,
            missing_fields=[],
            warnings=["test warning"],
            details={"key": "val"},
        )
        self.assertEqual(cc.exchange_type, ExchangeType.ALPACA)
        self.assertTrue(cc.is_complete)
        self.assertTrue(cc.is_valid)
        self.assertEqual(cc.warnings, ["test warning"])
        self.assertEqual(cc.details, {"key": "val"})


class TestCredentialInferenceDetectExchange(unittest.TestCase):
    def setUp(self):
        self.inference = CredentialInference()

    def test_empty_key_returns_unknown(self):
        result = self.inference.detect_exchange("")
        self.assertEqual(result, ExchangeType.UNKNOWN)

    def test_none_key_returns_unknown(self):
        result = self.inference.detect_exchange(None)
        self.assertEqual(result, ExchangeType.UNKNOWN)

    def test_alpaca_key_pk_prefix(self):
        result = self.inference.detect_exchange("PKABCDEFGHIJKLMNOPQRST")
        self.assertEqual(result, ExchangeType.ALPACA)

    def test_alpaca_key_ak_prefix(self):
        result = self.inference.detect_exchange("AKABCDEFGHIJKLMNOPQRST")
        self.assertEqual(result, ExchangeType.ALPACA)

    def test_alpaca_key_too_short(self):
        result = self.inference.detect_exchange("PK123")
        self.assertNotEqual(result, ExchangeType.ALPACA)

    def test_binance_64_hex_key(self):
        result = self.inference.detect_exchange("a" * 64)
        self.assertEqual(result, ExchangeType.BINANCE)

    def test_binance_64_char_key_not_hex(self):
        result = self.inference.detect_exchange("z" * 64)
        self.assertEqual(result, ExchangeType.BINANCE)

    def test_binance_length_range(self):
        result = self.inference.detect_exchange("x" * 65)
        self.assertEqual(result, ExchangeType.BINANCE)

    def test_bybit_length_with_secret(self):
        result = self.inference.detect_exchange("x" * 30, api_secret="some-secret")
        self.assertEqual(result, ExchangeType.BYBIT)

    def test_kraken_length_without_secret(self):
        result = self.inference.detect_exchange("x" * 30)
        self.assertEqual(result, ExchangeType.KRAKEN)

    def test_coinbase_or_okx_with_passphrase(self):
        result = self.inference.detect_exchange("x" * 30, passphrase="my-passphrase")
        self.assertEqual(result, ExchangeType.OKX)

    def test_solana_base58_key(self):
        solana_key = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" * 2
        solana_key = solana_key[:88]
        result = self.inference.detect_exchange(solana_key)
        self.assertEqual(result, ExchangeType.SOLANA)

    def test_unknown_key(self):
        result = self.inference.detect_exchange("xyz")
        self.assertEqual(result, ExchangeType.UNKNOWN)


class TestCredentialInferenceValidate(unittest.TestCase):
    def setUp(self):
        self.inference = CredentialInference()

    def test_alpaca_complete(self):
        check = self.inference.validate_credentials(
            exchange_type=ExchangeType.ALPACA,
            api_key = os.environ.get("TEST_API_KEY", "test_value"),
            api_secret="my-secret-key",
        )
        self.assertTrue(check.is_complete)
        self.assertEqual(check.missing_fields, [])

    def test_alpaca_missing_secret(self):
        check = self.inference.validate_credentials(
            exchange_type=ExchangeType.ALPACA,
            api_key = os.environ.get("TEST_API_KEY", "test_value"),
        )
        self.assertFalse(check.is_complete)
        self.assertIn("api_secret", check.missing_fields)

    def test_alpaca_missing_key(self):
        check = self.inference.validate_credentials(
            exchange_type=ExchangeType.ALPACA,
        )
        self.assertFalse(check.is_complete)
        self.assertIn("api_key", check.missing_fields)

    def test_binance_complete(self):
        check = self.inference.validate_credentials(
            exchange_type=ExchangeType.BINANCE,
            api_key="x" * 64,
            api_secret="my-secret",
        )
        self.assertTrue(check.is_complete)

    def test_coinbase_missing_passphrase(self):
        check = self.inference.validate_credentials(
            exchange_type=ExchangeType.COINBASE,
            api_key="x" * 30,
            api_secret="my-secret",
        )
        self.assertFalse(check.is_complete)
        self.assertIn("passphrase", check.missing_fields)

    def test_coinbase_complete(self):
        check = self.inference.validate_credentials(
            exchange_type=ExchangeType.COINBASE,
            api_key="x" * 30,
            api_secret="my-secret",
            passphrase="my-passphrase",
        )
        self.assertTrue(check.is_complete)

    def test_alpaca_wrong_prefix(self):
        check = self.inference.validate_credentials(
            exchange_type=ExchangeType.ALPACA,
            api_key = os.environ.get("TEST_API_KEY", "test_value"),
            api_secret="secret",
        )
        self.assertTrue(check.is_complete)
        self.assertGreater(len(check.warnings), 0)

    def test_key_too_short_for_expected_range(self):
        check = self.inference.validate_credentials(
            exchange_type=ExchangeType.ALPACA,
            api_key="PK",
            api_secret="secret",
        )
        self.assertTrue(check.is_complete)
        self.assertGreater(len(check.warnings), 0)

    def test_okx_requires_passphrase(self):
        check = self.inference.validate_credentials(
            exchange_type=ExchangeType.OKX,
            api_key="x" * 30,
            api_secret="secret",
            passphrase="pass",
        )
        self.assertTrue(check.is_complete)

    def test_bybit_complete(self):
        check = self.inference.validate_credentials(
            exchange_type=ExchangeType.BYBIT,
            api_key="x" * 30,
            api_secret="secret",
        )
        self.assertTrue(check.is_complete)


class TestCredentialInferenceGetRequiredFields(unittest.TestCase):
    def setUp(self):
        self.inference = CredentialInference()

    def test_alpaca_requires_key_and_secret(self):
        fields = self.inference.get_required_fields(ExchangeType.ALPACA)
        self.assertIn("api_key", fields)
        self.assertIn("api_secret", fields)
        self.assertNotIn("passphrase", fields)

    def test_coinbase_requires_passphrase(self):
        fields = self.inference.get_required_fields(ExchangeType.COINBASE)
        self.assertIn("api_key", fields)
        self.assertIn("api_secret", fields)
        self.assertIn("passphrase", fields)

    def test_solana_only_needs_key(self):
        fields = self.inference.get_required_fields(ExchangeType.SOLANA)
        self.assertIn("api_key", fields)
        self.assertNotIn("api_secret", fields)

    def test_unknown_requires_all(self):
        fields = self.inference.get_required_fields(ExchangeType.UNKNOWN)
        self.assertIn("api_key", fields)
        self.assertIn("api_secret", fields)

    def test_kraken_requires_key_and_secret(self):
        fields = self.inference.get_required_fields(ExchangeType.KRAKEN)
        self.assertIn("api_key", fields)
        self.assertIn("api_secret", fields)


class TestCredentialInferenceRepr(unittest.TestCase):
    def test_repr(self):
        inference = CredentialInference()
        result = repr(inference)
        self.assertIn("CredentialInference", result)
        self.assertIn("supported", result)


class TestExchangeKeyPatterns(unittest.TestCase):
    def test_all_exchanges_have_patterns(self):
        for ex in ExchangeType:
            if ex == ExchangeType.UNKNOWN:
                continue
            self.assertIn(ex, _EXCHANGE_KEY_PATTERNS)

    def test_alpaca_key_prefixes(self):
        pattern = _EXCHANGE_KEY_PATTERNS[ExchangeType.ALPACA]
        self.assertIn("PK", pattern["key_prefixes"])
        self.assertIn("AK", pattern["key_prefixes"])

    def test_solana_is_base58(self):
        pattern = _EXCHANGE_KEY_PATTERNS[ExchangeType.SOLANA]
        self.assertTrue(pattern["is_base58"])

    def test_all_have_key_length_range(self):
        for ex, pattern in _EXCHANGE_KEY_PATTERNS.items():
            self.assertIn("key_length_range", pattern)
            lo, hi = pattern["key_length_range"]
            self.assertLess(lo, hi)


if __name__ == "__main__":
    unittest.main(verbosity=2)
