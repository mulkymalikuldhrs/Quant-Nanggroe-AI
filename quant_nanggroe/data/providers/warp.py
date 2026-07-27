"""
WARP (1.1.1.1) connector — Cloudflare WARP route for QNA data pipeline.

Provides:
- OS/platform auto-detection for WARP config generation
- Cloudflare WARP API registration (free tier)
- WireGuard config generation
- Connection status detection (Android app / wg-quick / HTTP proxy)
- HTTP proxy routing via WARP's internal proxy (172.16.0.1:2480)

Integrates with proxy.py as a routing option between direct and SSH relay.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger("QNA.WARP")

WARP_API_BASE = "https://api.cloudflareclient.com/v0a1922"
WARP_PEER_PUBKEY = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="
WARP_ENDPOINT = "engage.cloudflareclient.com:2408"
WARP_HTTP_PROXY = "172.16.0.1:2480"

REG_PATH = Path.home() / ".config" / "qna" / "warp_reg.json"
CONF_PATH = Path("/etc/wireguard/warp.conf")


def _detect_platform() -> Dict[str, Any]:
    info = {
        "os": sys.platform,
        "machine": platform.machine(),
        "has_net_admin": False,
        "has_wg_quick": False,
        "is_termux": False,
        "warp_app_running": False,
    }
    if sys.platform == "linux":
        try:
            with open("/proc/1/comm") as f:
                init = f.read().strip()
            info["is_termux"] = "termux" in os.environ.get("HOME", "").lower() or "com.termux" in os.environ.get("PREFIX", "")
        except Exception:
            pass
        info["has_wg_quick"] = os.access("/usr/bin/wg-quick", os.X_OK) or os.access("/sbin/wg-quick", os.X_OK)
        try:
            r = subprocess.run(["wg", "show"], capture_output=True, text=True, timeout=3)
            info["has_net_admin"] = r.returncode == 0
        except Exception:
            info["has_net_admin"] = False
    if info["is_termux"]:
        try:
            r = subprocess.run(["dumpsys", "deviceidle", "get", "warp"], capture_output=True, text=True, timeout=3)
        except Exception:
            pass
    return info


def _warp_api_post(endpoint: str, data: dict) -> Optional[dict]:
    url = f"{WARP_API_BASE}/{endpoint}"
    payload = json.dumps(data)
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", url,
             "-H", "User-Agent: okhttp/3.12.1",
             "-H", "CF-Client-Version: a-6.3-1922",
             "-H", "Content-Type: application/json",
             "-d", payload],
            capture_output=True, text=True, timeout=20,
        )
        if r.returncode == 0 and r.stdout:
            return json.loads(r.stdout)
        if r.stderr:
            log.debug(f"WARP API POST {endpoint} stderr: {r.stderr[:100]}")
    except Exception as e:
        log.debug(f"WARP API POST {endpoint} exception: {e}")
    return None


def _warp_api_get(endpoint: str, token: str) -> Optional[dict]:
    url = f"{WARP_API_BASE}/{endpoint}"
    try:
        r = subprocess.run(
            ["curl", "-s", url,
             "-H", "User-Agent: okhttp/3.12.1",
             "-H", "CF-Client-Version: a-6.3-1922",
             "-H", f"Authorization: Bearer {token}"],
            capture_output=True, text=True, timeout=20,
        )
        if r.returncode == 0 and r.stdout:
            return json.loads(r.stdout)
        if r.stderr:
            log.debug(f"WARP API GET {endpoint} stderr: {r.stderr[:100]}")
    except Exception as e:
        log.debug(f"WARP API GET {endpoint} exception: {e}")
    return None


def _generate_keypair() -> Tuple[str, str]:
    try:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat
        priv = X25519PrivateKey.generate()
        priv_b64 = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        priv_key = __import__("base64").b64encode(priv_b64).decode()
        pub_b64 = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        pub_key = __import__("base64").b64encode(pub_b64).decode()
        return priv_key, pub_key
    except ImportError:
        priv = subprocess.run(["wg", "genkey"], capture_output=True, text=True, timeout=5)
        if priv.returncode == 0:
            priv_key = priv.stdout.strip()
            pub = subprocess.run(["wg", "pubkey"], input=priv_key, capture_output=True, text=True, timeout=5)
            pub_key = pub.stdout.strip() if pub.returncode == 0 else ""
            return priv_key, pub_key
        return "", ""


def register() -> Optional[Dict[str, Any]]:
    priv_key, pub_key = _generate_keypair()
    if not pub_key:
        log.error("Failed to generate WireGuard keypair")
        return None
    data = {
        "key": pub_key,
        "install_id": "",
        "fcm_token": "",
        "tos": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "Linux",
        "model": "Server",
        "locale": "en_US",
    }
    result = _warp_api_post("reg", data)
    if not result:
        return None
    device_id = result.get("id", "")
    token = result.get("token", "")
    if not device_id or not token:
        log.error("WARP registration missing id/token")
        return None
    config = _warp_api_get(f"reg/{device_id}", token)
    if not config:
        return None
    account = result.get("account", {})
    reg_data = {
        "device_id": device_id,
        "token": token,
        "private_key": priv_key,
        "public_key": pub_key,
        "account_type": account.get("account_type", "free"),
        "license": account.get("license", ""),
        "config": config.get("config", {}),
    }
    REG_PATH.parent.mkdir(parents=True, exist_ok=True)
    REG_PATH.write_text(json.dumps(reg_data, indent=2))
    log.info(f"WARP registered: device_id={device_id}, type={reg_data['account_type']}")
    return reg_data


def generate_config(reg: Optional[Dict] = None) -> Optional[str]:
    if reg is None:
        if REG_PATH.exists():
            reg = json.loads(REG_PATH.read_text())
        else:
            reg = register()
    if not reg:
        return None
    iface = reg.get("config", {}).get("interface", {})
    addr4 = iface.get("addresses", {}).get("v4", "172.16.0.2")
    addr6 = iface.get("addresses", {}).get("v6", "")
    priv_key = reg.get("private_key", "")
    conf = f"""[Interface]
PrivateKey = {priv_key}
Address = {addr4}/32
DNS = 1.1.1.1, 1.0.0.1
MTU = 1280

[Peer]
PublicKey = {WARP_PEER_PUBKEY}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = {WARP_ENDPOINT}
PersistentKeepalive = 25
"""
    if addr6:
        conf = conf.replace("Address = {addr4}/32", f"Address = {addr4}/32, {addr6}/128")
    return conf


def connect(conf_path: Path = CONF_PATH) -> bool:
    platform_info = _detect_platform()
    if platform_info["has_net_admin"] and platform_info["has_wg_quick"]:
        conf = generate_config()
        if not conf:
            return False
        conf_path.parent.mkdir(parents=True, exist_ok=True)
        conf_path.write_text(conf)
        try:
            r = subprocess.run(["wg-quick", "up", str(conf_path)], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                log.info("WARP connected via wg-quick")
                return True
            log.warning(f"wg-quick failed: {r.stderr[:200]}")
        except Exception as e:
            log.warning(f"wg-quick error: {e}")
        return False
    plat = _detect_platform()
    if plat["is_termux"]:
        log.info("WARP: Termux detected — use 1.1.1.1 app on Android or wireguard-go")
    log.info("WARP: net_admin not available — skipping kernel WireGuard")
    return False


def disconnect() -> bool:
    try:
        r = subprocess.run(["wg-quick", "down", str(CONF_PATH)], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def is_connected() -> bool:
    try:
        r = subprocess.run(["wg", "show", "warp"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            return True
    except Exception:
        pass
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("172.16.0.1", 2480))
        s.close()
        if result == 0:
            return True
    except Exception:
        pass
    return False


def get_proxy_url() -> Optional[str]:
    if is_connected():
        return f"http://{WARP_HTTP_PROXY}"
    return None


def status() -> Dict[str, Any]:
    plat = _detect_platform()
    connected = is_connected()
    reg_info = None
    if REG_PATH.exists():
        reg_info = json.loads(REG_PATH.read_text())
    return {
        "connected": connected,
        "platform": plat,
        "registered": REG_PATH.exists(),
        "account_type": reg_info.get("account_type", "none") if reg_info else "none",
        "device_id": reg_info.get("device_id", "")[:8] + "..." if reg_info and reg_info.get("device_id") else "",
        "proxy_url": get_proxy_url(),
        "wg_interface": os.path.exists("/sys/class/net/warp"),
    }
