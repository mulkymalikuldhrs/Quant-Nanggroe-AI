import httpx
from fastapi import APIRouter, Request, Response

router = APIRouter()

@router.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy(request: Request, full_path: str):
    """Proxy any request to the local Otto MCP service.
    The Otto service runs on http://localhost:8765. This endpoint forwards
    the incoming request method, path, query parameters, headers, and body
    to the Otto service and returns its response back to the caller.
    """
    # Build the target URL preserving query string
    target_url = f"http://localhost:8765/{full_path}" + ("?" + request.url.query if request.url.query else "")
    # Prepare request data
    method = request.method.lower()
    headers = dict(request.headers)
    # Exclude "host" header to avoid mismatches
    headers.pop("host", None)
    body = await request.body()
    async with httpx.AsyncClient() as client:
        # Dispatch request to Otto service
        response = await client.request(method, target_url, headers=headers, content=body, timeout=30.0)
    # Return response to caller
    return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))
