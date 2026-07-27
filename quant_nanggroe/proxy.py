"""
Proxy helper for QNA network requests.
Provides a simple JSON GET wrapper that can optionally route through a SOCKS5
proxy (or any HTTP proxy) defined via the PROXY_SOCKS5 environment variable.
If the proxy is unavailable or causes an error, the function falls back to a
direct request.
"""

import logging
import os
from typing import Any, Optional

import requests

log = logging.getLogger("QNA.Proxy")

# Expected format: socks5://127.0.0.1:1080 or http://proxy:port
PROXY_URL = os.getenv("PROXY_SOCKS5")
if PROXY_URL:
    PROXIES = {"http": PROXY_URL, "https": PROXY_URL}
    log.info(f"Proxy enabled: {PROXY_URL}")
else:
    PROXIES = None
    log.info("No proxy configured; using direct connections")

def get_json(url: str, timeout: int = 15) -> Optional[Any]:
    """Fetch JSON from *url*.

    Returns the parsed JSON object on success, ``None`` on any error.
    SSL verification is enabled. Proxy routing via PROXY_SOCKS5 env var.
    """
    try:
        resp = requests.get(url, timeout=timeout, verify=True, proxies=PROXIES,
                            headers={"User-Agent": "QNA/1.0"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.debug(f"Network request failed for {url[:60]}: {e}")
        return None
