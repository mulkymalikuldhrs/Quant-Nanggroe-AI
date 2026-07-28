"""MCP protocol: server and protocol implementation."""

# Package init (client.py + tools.py archived — server uses different path)

__all__ = [
    'protocol',
    'server',
]

from . import protocol, server
