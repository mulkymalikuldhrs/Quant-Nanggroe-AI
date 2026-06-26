"""AgenticTrading-inspired protocol abstractions."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ProtocolMessage:
    source: str
    target: str
    action: str
    payload: Dict[str, Any]


class ProtocolAdapter(ABC):
    @abstractmethod
    def send(self, msg: ProtocolMessage) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def receive(self) -> Optional[ProtocolMessage]: ...


class MCPAdapter(ProtocolAdapter):
    """MCP protocol adapter - connects to MCP servers."""

    def __init__(self, server_url: str):
        self.server_url = server_url

    def send(self, msg: ProtocolMessage) -> Optional[Dict[str, Any]]:
        import requests
        try:
            resp = requests.post(
                f"{self.server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": msg.action,
                    "params": msg.payload,
                    "id": msg.source,
                },
                timeout=10,
            )
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def receive(self) -> Optional[ProtocolMessage]:
        return None
