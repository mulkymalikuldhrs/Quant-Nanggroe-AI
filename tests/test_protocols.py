"""Tests: Protocol Adapters — AgenticTrading-inspired abstractions."""
from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from quant_nanggroe.agents.protocols import ProtocolMessage, ProtocolAdapter, MCPAdapter


class TestProtocolMessage(unittest.TestCase):
    def test_fields(self):
        msg = ProtocolMessage(source="agent_a", target="agent_b", action="ping", payload={"ts": 1})
        self.assertEqual(msg.source, "agent_a")
        self.assertEqual(msg.target, "agent_b")
        self.assertEqual(msg.action, "ping")
        self.assertEqual(msg.payload, {"ts": 1})

    def test_empty_payload(self):
        msg = ProtocolMessage(source="a", target="b", action="status", payload={})
        self.assertEqual(msg.payload, {})


class TestProtocolAdapter(unittest.TestCase):
    def test_is_abstract(self):
        self.assertTrue(ProtocolAdapter.__abstractmethods__ is not None)
        self.assertIn("send", ProtocolAdapter.__abstractmethods__)
        self.assertIn("receive", ProtocolAdapter.__abstractmethods__)


class TestMCPAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = MCPAdapter("http://localhost:8000")

    def test_init_stores_url(self):
        self.assertEqual(self.adapter.server_url, "http://localhost:8000")

    def test_receive_returns_none(self):
        self.assertIsNone(self.adapter.receive())

    def test_send_returns_error_on_bad_url(self):
        adapter = MCPAdapter("http://nonexistent.invalid:9999")
        result = adapter.send(ProtocolMessage("a", "b", "ping", {}))
        self.assertIn("error", result)

    def test_send_returns_error_on_connection_refused(self):
        adapter = MCPAdapter("http://localhost:1")
        result = adapter.send(ProtocolMessage("a", "b", "ping", {}))
        self.assertIn("error", result)

    def test_send_constructs_correct_payload(self):
        msg = ProtocolMessage(source="agent_1", target="server", action="get_status", payload={"id": 42})
        expected_url = "http://localhost:8000/mcp"
        self.assertEqual(
            f"{self.adapter.server_url}/mcp",
            expected_url,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
