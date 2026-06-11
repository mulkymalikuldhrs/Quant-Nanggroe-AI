"""Tests for API."""
import pytest
from ai_multicolony.api.app import create_app

class TestAPI:
    def test_create_app(self):
        app = create_app()
        assert app is not None
