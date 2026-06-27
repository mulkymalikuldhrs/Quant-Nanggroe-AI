# Seulanga RAG bridge — persistent memory via MCP
# Connects to Seulanga MCP server at port 3100

import os
import httpx
import json
from typing import Optional

SEULANGA_MCP_URL = os.getenv("SEULANGA_MCP_URL", "http://127.0.0.1:3100/mcp")


async def seulanga_learn(content: str, source: str = "qna", tags: Optional[list] = None) -> dict:
    """Store knowledge in Seulanga RAG memory."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(SEULANGA_MCP_URL, json={
                "jsonrpc": "2.0",
                "method": "seulanga_learn",
                "params": {"content": content, "source": source, "tags": tags or []},
                "id": 1
            })
            return r.json()
    except Exception as e:
        return {"error": str(e)}


async def seulanga_search(query: str, limit: int = 5) -> dict:
    """Search Seulanga RAG memory."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(SEULANGA_MCP_URL, json={
                "jsonrpc": "2.0",
                "method": "seulanga_search",
                "params": {"query": query, "limit": limit},
                "id": 1
            })
            return r.json()
    except Exception as e:
        return {"error": str(e)}
