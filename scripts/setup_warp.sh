#!/usr/bin/env bash
# =============================================================================
# QNA WARP (1.1.1.1) Setup — Auto-detect OS, register, connect
# =============================================================================
# Detects platform, installs prerequisites, registers with Cloudflare WARP,
# generates WireGuard config, and connects. Also verifies data routing works.
#
# Usage:
#   bash scripts/setup_warp.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()    { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

echo ""
echo -e "${CYAN}==================================================${NC}"
echo -e "${CYAN}  QNA WARP (1.1.1.1) — Connectivity Setup${NC}"
echo -e "${CYAN}==================================================${NC}"
echo ""

# ---------------------------------------------------------------------------
# 1. Auto-detect platform
# ---------------------------------------------------------------------------
info "Detecting platform..."
OS="$(uname -s)"
ARCH="$(uname -m)"
IS_TERMUX=false
IS_ALPINE=false
HAS_NET_ADMIN=false
HAS_WG=false
HAS_CURL=false

if [ -f /etc/alpine-release ]; then
    IS_ALPINE=true
    info "  OS: Alpine Linux $(cat /etc/alpine-release)"
fi

if echo "$HOME" | grep -qi "termux" || [ -n "${TERMUX_VERSION:-}" ]; then
    IS_TERMUX=true
    info "  Environment: Termux (Android)"
fi

command -v wg &>/dev/null && HAS_WG=true && info "  WireGuard: installed"
command -v curl &>/dev/null && HAS_CURL=true && info "  curl: installed"

if $HAS_WG; then
    if wg show &>/dev/null 2>&1; then
        HAS_NET_ADMIN=true
        info "  Net admin: available"
    else
        warn "  Net admin: NOT available (wg-quick will fail)"
    fi
fi

info "  Architecture: $ARCH"

# ---------------------------------------------------------------------------
# 2. Install prerequisites
# ---------------------------------------------------------------------------
if ! $HAS_CURL; then
    info "Installing curl..."
    if $IS_ALPINE; then apk add curl; fi
fi

if ! $HAS_WG; then
    info "Installing wireguard-tools..."
    if $IS_ALPINE; then apk add wireguard-tools wireguard-tools-wg-quick; fi
fi

# ---------------------------------------------------------------------------
# 3. Check Python 3
# ---------------------------------------------------------------------------
info "Checking Python..."
PYTHON=""
for p in python3.12 python3.11 python3; do
    if command -v "$p" &>/dev/null; then
        PYTHON="$p"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    fail "Python 3 not found. Install it first."
fi
PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
success "Python $PY_VER found"

# ---------------------------------------------------------------------------
# 4. Register with Cloudflare WARP
# ---------------------------------------------------------------------------
info "Registering with Cloudflare WARP API..."
REG_DATA=$(python3.12 -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT')
from quant_nanggroe.providers.warp import register
import json
r = register()
if r:
    print(json.dumps({'ok': True, 'device_id': r['device_id'], 'type': r['account_type']}))
else:
    print(json.dumps({'ok': False}))
" 2>&1)

if echo "$REG_DATA" | grep -q '"ok": true'; then
    DEVICE_ID=$(echo "$REG_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['device_id'])")
    ACCT_TYPE=$(echo "$REG_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['type'])")
    success "WARP registered: device=$DEVICE_ID type=$ACCT_TYPE"
else
    fail "WARP registration failed. Check network connectivity."
fi

# ---------------------------------------------------------------------------
# 5. Generate and connect
# ---------------------------------------------------------------------------
if $HAS_NET_ADMIN && $HAS_WG; then
    info "Generating WARP WireGuard config..."
    $PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT')
from quant_nanggroe.providers.warp import generate_config, connect
conf = generate_config()
if conf:
    with open('/etc/wireguard/warp.conf', 'w') as f:
        f.write(conf)
    print('Config written')
else:
    print('Config generation failed')
" 2>&1

    info "Attempting WARP connection (wg-quick)..."
    if wg-quick up /etc/wireguard/warp.conf 2>&1; then
        success "WARP connected!"
    else
        warn "wg-quick failed (may need root/net_admin)"
    fi
else
    warn "WireGuard kernel interface not available"
    warn "WARP config generated at ~/.config/qna/warp_reg.json"
    info "Options:"
    if $IS_TERMUX; then
        info "  1. Enable 1.1.1.1 app on Android (WARP VPN)"
        info "  2. Use wireguard-go (userspace): pkg install wireguard-go"
    fi
    info "  3. Use SSH relay (already configured): direct → SSH relay"
fi

# ---------------------------------------------------------------------------
# 6. Verify data routing
# ---------------------------------------------------------------------------
info "Verifying data routing..."
echo ""
echo -e "  ${CYAN}Route 1: WARP proxy check${NC}"
if $PYTHON -c "
import socket
s = socket.socket()
s.settimeout(2)
r = s.connect_ex(('172.16.0.1', 2480))
s.close()
print('available' if r == 0 else 'unavailable')
" 2>/dev/null | grep -q "available"; then
    success "  WARP HTTP proxy (172.16.0.1:2480) detected"
else
    warn "  WARP HTTP proxy not available"
fi

echo -e "  ${CYAN}Route 2: SSH relay${NC}"
if nc -z -w3 10.210.13.229 8022 2>/dev/null; then
    success "  SSH relay (10.210.13.229:8022) reachable"
else
    warn "  SSH relay not reachable"
fi

echo -e "  ${CYAN}Route 3: Bybit via proxy chain${NC}"
$PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT')
from quant_nanggroe.providers.proxy import get_json
d = get_json('https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT', timeout=25)
if d:
    t = d.get('result',{}).get('list',[{}])[0]
    print(f'BTCUSDT: {t.get(\"lastPrice\",\"?\")}')
else:
    print('FAILED')
" 2>&1 | grep -E "BTCUSDT|FAILED"

echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  WARP Setup Complete${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""
echo -e "  Next steps:"
echo -e "  ${CYAN}1.${NC} Check routing: python3 -m quant_nanggroe.providers.warp"
echo -e "  ${CYAN}2.${NC} Dashboard: python3 -m quant_nanggroe.live_engine dashboard"
echo -e "  ${CYAN}3.${NC} If using Android 1.1.1.1 app:"
echo -e "     - Open 1.1.1.1 app → enable WARP VPN"
echo -e "     - Verify: curl -x http://172.16.0.1:2480 https://api.bybit.com/..."
echo ""
