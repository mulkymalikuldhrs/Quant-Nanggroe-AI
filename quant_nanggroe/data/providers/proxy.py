"""
Proxy helper for QNA network requests — routes through WARP or SSH relay for ISP bypass.

Tries in order:
1. Direct httpx (may be blocked by Telkomsel SNI filtering)
2. WARP HTTP proxy (172.16.0.1:2480) if Cloudflare 1.1.1.1 app/WARP is active
3. SSH relay fallback (curl via remote 10.210.13.229:8022)

When PROXY_SOCKS5 env var is set, adds socks5 proxy to direct requests.
"""
import json
import logging
import os
import shlex
import subprocess
from typing import Optional, Any

log = logging.getLogger("QNA.Proxy")

PROXY_URL = os.getenv("PROXY_SOCKS5")

_SSH_ARGS = [
    "ssh", "-o", "StrictHostKeyChecking=no",
    "-o", "ConnectTimeout=10",
    "-p", "8022",
    "u0_a467@10.210.13.229",
]


def _ssh_curl(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch URL via SSH -> curl on remote host (bypasses ISP blocking)."""
    safe_url = shlex.quote(url)
    cmd = _SSH_ARGS + ["curl", "-s", "--max-time", str(timeout),
                        "-H", "User-Agent: QNA/1.0", safe_url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        if r.returncode == 0 and r.stdout:
            return r.stdout
        if r.stderr:
            log.debug(f"SSH curl stderr: {r.stderr[:100]}")
    except Exception as e:
        log.debug(f"SSH curl exception: {e}")
    return None


_WARP_PROXY_CACHED: Optional[bool] = None
_WARP_WORKING: Optional[bool] = None

def _warp_proxy_available() -> bool:
    global _WARP_PROXY_CACHED
    if _WARP_PROXY_CACHED is not None:
        return _WARP_PROXY_CACHED
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("172.16.0.1", 2480))
        s.close()
        _WARP_PROXY_CACHED = result == 0
        if _WARP_PROXY_CACHED:
            log.info("WARP HTTP proxy detected at 172.16.0.1:2480")
    except Exception:
        _WARP_PROXY_CACHED = False
    return _WARP_PROXY_CACHED


def get_json(url: str, timeout: int = 15) -> Optional[Any]:
    # 1. Try direct httpx
    try:
        import httpx
        kwargs = {"timeout": httpx.Timeout(timeout, connect=5.0), "verify": False}
        if PROXY_URL:
            kwargs["proxy"] = PROXY_URL
        with httpx.Client(**kwargs) as client:
            resp = client.get(url, headers={"User-Agent": "QNA/1.0"})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.debug(f"Direct request failed for {url[:60]}: {e}")

    # 2. Fallback: WARP HTTP proxy (Cloudflare 1.1.1.1) if available
    if _warp_proxy_available():
        try:
            with httpx.Client(proxy=f"http://172.16.0.1:2480", timeout=httpx.Timeout(5.0, connect=3.0), verify=True) as client:
                resp = client.get(url, headers={"User-Agent": "QNA/1.0"})
                resp.raise_for_status()
                log.info(f"Got response via WARP proxy for {url[:60]}")
                return resp.json()
        except Exception as e:
            log.debug(f"WARP proxy failed for {url[:60]}: {e}")

    # 3. Fallback: SSH relay via curl on remote
    log.info(f"Trying SSH relay for {url[:60]}")
    raw = _ssh_curl(url, timeout)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            log.debug(f"SSH relay non-JSON response for {url[:60]}")
    return None
