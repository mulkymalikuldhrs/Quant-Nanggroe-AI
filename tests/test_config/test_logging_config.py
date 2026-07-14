"""Tests: Logging configuration — setup_logging, structlog fallback, PII redaction.

All tests are deterministic — no network calls or external dependencies.
"""

from __future__ import annotations

import logging
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from quant_nanggroe.config.logging_config import (
    setup_logging,
    get_logger,
)


class TestSetupLogging(unittest.TestCase):
    def setUp(self):
        logging.shutdown()
        # Remove all handlers from root logger
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)

    def tearDown(self):
        logging.shutdown()
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)

    @patch("quant_nanggroe.config.logging_config.structlog", None)
    def test_setup_stdlib_fallback(self):
        setup_logging(level="INFO", format_type="console")
        root = logging.getLogger()
        self.assertGreater(len(root.handlers), 0)

    @patch("quant_nanggroe.config.logging_config.structlog", None)
    def test_setup_stdlib_json_format(self):
        setup_logging(level="DEBUG", format_type="json")
        root = logging.getLogger()
        self.assertGreater(len(root.handlers), 0)

    @patch("quant_nanggroe.config.logging_config.structlog", None)
    def test_stdlib_logger_works(self):
        setup_logging(level="WARNING")
        logger = get_logger("test_stdlib")
        # Should not raise
        logger.warning("test warning message")

    @patch("quant_nanggroe.config.logging_config.structlog", None)
    def test_setup_with_invalid_level_defaults_to_info(self):
        setup_logging(level="INVALID_LEVEL")
        root = logging.getLogger()
        self.assertEqual(root.level, logging.INFO)

    @patch("quant_nanggroe.config.logging_config.structlog", None)
    def test_setup_log_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        try:
            setup_logging(level="INFO", log_file=log_path)
            logger = get_logger("test_file")
            logger.info("test log message")
            logging.shutdown()
            with open(log_path) as f:
                content = f.read()
            self.assertIn("test log message", content)
        finally:
            try:
                os.unlink(log_path)
            except PermissionError:
                pass  # Windows: file may still be locked by handler

    @patch("quant_nanggroe.config.logging_config.structlog", None)
    def test_setup_different_levels(self):
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            with self.subTest(level=level):
                logging.shutdown()
                root = logging.getLogger()
                for handler in list(root.handlers):
                    root.removeHandler(handler)
                setup_logging(level=level)
                root = logging.getLogger()
                expected = getattr(logging, level)
                self.assertEqual(root.level, expected)


class TestSetupLoggingWithStructlog(unittest.TestCase):
    def setUp(self):
        logging.shutdown()
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)

    def tearDown(self):
        logging.shutdown()
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)

    @patch("quant_nanggroe.config.logging_config.structlog")
    def test_setup_with_structlog_json(self, mock_structlog):
        mock_structlog.get_logger.return_value = MagicMock()
        setup_logging(level="INFO", format_type="json")
        mock_structlog.configure.assert_called_once()

    @patch("quant_nanggroe.config.logging_config.structlog")
    def test_setup_with_structlog_console(self, mock_structlog):
        mock_structlog.get_logger.return_value = MagicMock()
        setup_logging(level="DEBUG", format_type="console")
        mock_structlog.configure.assert_called_once()

    @patch("quant_nanggroe.config.logging_config.structlog")
    def test_structlog_levels(self, mock_structlog):
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            with self.subTest(level=level):
                logging.shutdown()
                root = logging.getLogger()
                for handler in list(root.handlers):
                    root.removeHandler(handler)
                mock_structlog.reset_mock()
                setup_logging(level=level)
                self.assertTrue(mock_structlog.configure.called)

    @patch("quant_nanggroe.config.logging_config.structlog")
    def test_structlog_log_file(self, mock_structlog):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        try:
            setup_logging(level="INFO", log_file=log_path)
            # Should not raise
            self.assertTrue(mock_structlog.configure.called)
        finally:
            try:
                os.unlink(log_path)
            except PermissionError:
                pass  # Windows: file may still be locked by handler


class TestGetLogger(unittest.TestCase):
    def setUp(self):
        logging.shutdown()
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)

    def tearDown(self):
        logging.shutdown()
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)

    @patch("quant_nanggroe.config.logging_config.structlog", None)
    def test_get_logger_stdlib(self):
        logger = get_logger("test.stdlib")
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test.stdlib")

    @patch("quant_nanggroe.config.logging_config.structlog")
    def test_get_logger_structlog(self, mock_structlog):
        mock_logger = MagicMock()
        mock_structlog.get_logger.return_value = mock_logger
        result = get_logger("test.structured")
        self.assertEqual(result, mock_logger)
        mock_structlog.get_logger.assert_called_once_with("test.structured")


class TestGetLoggerEdgeCases(unittest.TestCase):
    @patch("quant_nanggroe.config.logging_config.structlog", None)
    def test_get_logger_empty_name(self):
        logger = get_logger("")
        self.assertIsInstance(logger, logging.Logger)

    @patch("quant_nanggroe.config.logging_config.structlog", None)
    def test_get_logger_with_dots(self):
        logger = get_logger("quant_nanggroe.engine.risk.kill_switch")
        self.assertEqual(logger.name, "quant_nanggroe.engine.risk.kill_switch")


if __name__ == "__main__":
    unittest.main(verbosity=2)
