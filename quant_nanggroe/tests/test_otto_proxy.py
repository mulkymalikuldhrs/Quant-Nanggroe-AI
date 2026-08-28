from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from quant_nanggroe.api.app import app


@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_otto_proxy_forward(client):
    """Ensure the Otto proxy forwards request to the local Otto service and returns the response."""
    mock_httpx_response = httpx.Response(status_code=200, content=b"ok")
    async_request_mock = AsyncMock(return_value=mock_httpx_response)

    async def mock_client_enter(*args, **kwargs):
        return type("MockClient", (), {"request": async_request_mock})()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.side_effect = mock_client_enter
        mock_client_cls.return_value.__aexit__.return_value = AsyncMock()
        response = client.get("/api/otto/test?foo=bar")
        assert response.status_code == 200
        assert response.content == b"ok"
        async_request_mock.assert_awaited_once()
        method, url = async_request_mock.call_args[0]
        assert method == "get"
        assert url == "http://localhost:8765/test?foo=bar"
