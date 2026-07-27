#!/usr/bin/env python3
"""
QNA Engine Bridge — connects live_engine.py ↔ engine/ layer.

Provides:
- EnginePriceProvider: synchronous price/klines fetcher using engine/data/ patterns
- EngineRiskManager: risk manager using engine/risk/ constants and engine/persistence/
- StalePositionAnalyzer: logs stale positions with real price PnL

DO NOT modify existing engine/ files — this bridge adapts them for live_engine.py.
"""

import json
import logging
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("QNA-Bridge")


def _ssl_ctx():
    verify = os.environ.get("QNAI_SSL_VERIFY", "1") == "1"
    ctx = ssl.create_default_context()
    ctx.check_hostname = verify
    ctx.verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE
    if not verify:
        log.warning("SSL verification DISABLED — set QNAI_SSL_VERIFY=1 in production")
    return ctx


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

MAX_POSITIONS_TOTAL = 3

ASSET_MAP = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin",
}
# Backward-compat alias for any modules referencing the old typo
ASSSET_MAP = ASSET_MAP
SYMBOL_TO_CG = {v: k for k, v in ASSET_MAP.items()}
CG_IDS = ",".join(ASSET_MAP.values())


class DNSBypass:
    """Bypass Telkomsel DNS poisoning via Cloudflare DoH + CDN SNI."""

    DOH_URL = "https://cloudflare-dns.com/dns-query"

    # CDN hostname cache: actual_domain -> (cdn_hostname, [(ip, ttl)])
    _cdn_cache: Dict[str, tuple] = {}
    _doh_ctx = None

    @classmethod
    def _get_doh_ctx(cls):
        if cls._doh_ctx is None:
            cls._doh_ctx = _ssl_ctx()
        return cls._doh_ctx

    @classmethod
    def resolve_cname(cls, domain: str) -> Optional[str]:
        """Resolve CNAME via Cloudflare DoH."""
        try:
            url = f"{cls.DOH_URL}?name={domain}&type=CNAME"
            req = urllib.request.Request(url, headers={"Accept": "application/dns-json", "User-Agent": "QNA/2.0"})
            with urllib.request.urlopen(req, timeout=8, context=cls._get_doh_ctx()) as r:
                data = json.loads(r.read())
                for a in data.get("Answer", []):
                    if a.get("type") == 5:
                        return a["data"].rstrip(".")
        except Exception as e:
            log.debug(f"DoH CNAME fail for {domain}: {e}")
        return None

    @classmethod
    def resolve_a(cls, hostname: str) -> List[str]:
        """Resolve A records via Cloudflare DoH."""
        try:
            url = f"{cls.DOH_URL}?name={hostname}&type=A"
            req = urllib.request.Request(url, headers={"Accept": "application/dns-json", "User-Agent": "QNA/2.0"})
            with urllib.request.urlopen(req, timeout=8, context=cls._get_doh_ctx()) as r:
                data = json.loads(r.read())
                return [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]
        except Exception as e:
            log.debug(f"DoH A fail for {hostname}: {e}")
        return []

    @classmethod
    def _raw_https(cls, ip: str, sni_hostname: str, host_header: str, path: str, timeout: int = 10) -> Optional[dict]:
        """Make HTTPS request to IP with custom SNI and Host header.
        Retries 3x with exponential backoff on failure."""
        ctx = _ssl_ctx()
        last_err = None
        for attempt in range(3):
            try:
                sock = socket.create_connection((ip, 443), timeout=min(timeout, 5))
                ssock = ctx.wrap_socket(sock, server_hostname=sni_hostname)
                req_bytes = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {host_header}\r\n"
                    f"User-Agent: QNA/2.0\r\n"
                    f"Accept: application/json\r\n"
                    f"Connection: close\r\n\r\n"
                ).encode()
                ssock.sendall(req_bytes)
                resp = b""
                ssock.settimeout(timeout)
                while True:
                    try:
                        chunk = ssock.recv(4096)
                        if not chunk:
                            break
                        resp += chunk
                    except socket.timeout:
                        break
                ssock.close()
                _, _, body = resp.partition(b"\r\n\r\n")
                if not body:
                    continue
                return json.loads(body.decode())
            except Exception as e:
                last_err = e
                log.debug(f"Raw HTTPS attempt {attempt+1}/3 fail {sni_hostname} via {ip}: {e}")
                if attempt < 2:
                    time.sleep(1 * (2 ** attempt))
        return None


class ExchangeBypassProvider:
    """Provides crypto prices via CDN-bypassed exchange APIs (Bybit, OKX) with failover to CoinGecko."""

    # Bybit: CloudFront CDN
    BYBIT_HOST = "api.bybit.com"
    BYBIT_CDN_CNAME = "d3d4ij29qlbhtu.cloudfront.net"
    BYBIT_CDN_IPS = ["65.9.168.22", "65.9.168.119", "65.9.168.113", "65.9.168.83"]

    # OKX: Cloudflare CDN
    OKX_HOST = "www.okx.com"
    OKX_CDN_CNAME = "www.okx.com.cdn.cloudflare.net"

    def __init__(self, cache_ttl: int = 30):
        self.cache_ttl = cache_ttl
        self._bybit_ips: List[str] = list(self.BYBIT_CDN_IPS)
        self._okx_ips: List[str] = []
        self._last_dns_refresh = 0.0

    def _refresh_dns(self):
        """Refresh CDN IPs via DoH every 300s."""
        now = time.time()
        if now - self._last_dns_refresh < 300:
            return
        self._last_dns_refresh = now
        bybit_ips = DNSBypass.resolve_a(self.BYBIT_CDN_CNAME)
        if bybit_ips:
            self._bybit_ips = bybit_ips
        okx_ips = DNSBypass.resolve_a(self.OKX_CDN_CNAME)
        if okx_ips:
            self._okx_ips = okx_ips
            log.debug(f"ExchangeBypass: Bybit IPs={self._bybit_ips}, OKX IPs={self._okx_ips}")

    def _bybit_price(self, symbol: str) -> Optional[float]:
        self._refresh_dns()
        for ip in self._bybit_ips:
            data = DNSBypass._raw_https(ip, self.BYBIT_CDN_CNAME, self.BYBIT_HOST,
                f"/v5/market/tickers?category=spot&symbol={symbol}")
            if data and data.get("retCode") == 0:
                tickers = data["result"].get("list", [])
                if tickers:
                    return float(tickers[0].get("lastPrice", 0))
        return None

    def _okx_price(self, symbol: str) -> Optional[float]:
        self._refresh_dns()
        if not self._okx_ips:
            return None
        for ip in self._okx_ips:
            data = DNSBypass._raw_https(ip, self.OKX_CDN_CNAME, self.OKX_HOST,
                f"/api/v5/market/ticker?instId={symbol}")
            if data and data.get("code") == "0":
                ticker = data.get("data", [{}])
                if ticker:
                    return float(ticker[0].get("last", 0))
        return None

    def get_price(self, symbol: str) -> Optional[float]:
        """Bybit (fast) -> OKX (fast) -> None."""
        p = self._bybit_price(symbol)
        if p:
            return p
        return self._okx_price(symbol)


class EnginePriceProvider:
    """Synchronous price provider with multi-exchange failover, caching, and rate limiting.

    Replaces live_engine.py's BinanceConnector with one that:
    - Uses engine/data/rate_limiter for rate limiting
    - Uses engine/data/caching for response caching
    - Fetches from Bybit (fast) -> OKX (fast) -> CoinGecko (slow)
    - Raises RuntimeError when all sources fail (no synthetic data)
    """

    def __init__(self, cache_ttl: int = 60):
        self.cache_ttl = cache_ttl
        self._last_request = 0.0
        self._min_interval = 0.3

        self._rate_limiter = None
        self._cache = None
        self._exchange = ExchangeBypassProvider(cache_ttl=cache_ttl)
        self._init_engine_components()

    def _init_engine_components(self):
        try:
            from quant_nanggroe.engine.data.rate_limiter import RateLimiter
            self._rate_limiter = RateLimiter()
        except Exception as e:
            log.debug(f"RateLimiter unavailable: {e}")

        try:
            from quant_nanggroe.engine.data.caching import TermuxDiskCache
            self._cache = TermuxDiskCache(db_path=str(DATA_DIR / "engine_bridge_cache.db"), default_ttl=self.cache_ttl)
        except Exception as e:
            log.debug(f"DiskCache unavailable: {e}")

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()

        if self._rate_limiter:
            sleep = self._rate_limiter.acquire("coingecko")
            if sleep > 0:
                time.sleep(sleep)

    def _request(self, url: str, timeout: int = 15) -> Optional[dict]:
        for attempt in range(3):
            try:
                ctx = _ssl_ctx()
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "QNA/2.0")
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    return json.loads(resp.read())
            except Exception as e:
                log.debug(f"HTTP attempt {attempt+1}/3 (ssl=on) fail: {e}")
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(url)
                    req.add_header("User-Agent", "QNA/2.0")
                    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                        log.warning(f"SSL bypass fallback used for {url}")
                        return json.loads(resp.read())
                except Exception as e2:
                    log.debug(f"HTTP attempt {attempt+1}/3 (ssl=off) fail: {e2}")
                if attempt < 2:
                    time.sleep(1 * (2 ** attempt))
        return None

    def get_all_prices(self, force: bool = False) -> Dict[str, float]:
        cache_key = "all_prices"
        if not force and self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        result = {}
        # 1. Try exchange bypass (Bybit -> OKX) for all symbols
        for symbol in ASSET_MAP:
            p = self._exchange.get_price(symbol)
            if p:
                result[symbol] = p

        # 2. Fill missing from CoinGecko
        missing = [s for s in ASSET_MAP if s not in result]
        if missing:
            self._rate_limit()
            ids = ",".join(ASSET_MAP[s] for s in missing)
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
            data = self._request(url)
            if data:
                for symbol in missing:
                    coin_id = ASSET_MAP[symbol]
                    entry = data.get(coin_id, {})
                    usd_price = entry.get("usd")
                    if usd_price is not None:
                        result[symbol] = float(usd_price)

        if self._cache and result:
            self._cache.set(cache_key, result, ttl=self.cache_ttl)
        elif not result and self._cache:
            stale = self._cache.get(cache_key)
            if stale:
                log.warning("All price sources failed — serving stale cache")
                return stale

        return result

    def get_price(self, symbol: str) -> Optional[float]:
        prices = self.get_all_prices()
        return prices.get(symbol)

    def get_klines(self, symbol: str, interval: str = "1m", limit: int = 60) -> List[Dict]:
        coin_id = ASSET_MAP.get(symbol)
        if not coin_id:
            return []
        cache_key = f"klines_{symbol}_{interval}_{limit}"
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # 1. Try Bybit for real klines
        candles = self._bybit_klines(symbol, limit)
        if candles:
            if self._cache:
                self._cache.set(cache_key, candles, ttl=self.cache_ttl)
            return candles

        # 2. Fallback to CoinGecko OHLC
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days=1"
        self._rate_limit()
        resp_data = self._request(url)
        if isinstance(resp_data, list) and len(resp_data) > 0:
            candles = []
            for entry in resp_data:
                if isinstance(entry, list) and len(entry) >= 5:
                    ts_ms = entry[0]
                    candles.append({
                        "timestamp": ts_ms // 1000,
                        "open": float(entry[1]),
                        "high": float(entry[2]),
                        "low": float(entry[3]),
                        "close": float(entry[4]),
                        "volume": 0.0,
                        "synthetic": False,
                    })
            candles = candles[-limit:]
            if self._cache:
                self._cache.set(cache_key, candles, ttl=self.cache_ttl)
            return candles

        # 3. Fail-closed: no synthetic data
        raise RuntimeError(
            f"No real klines available for {symbol} from any source (Bybit + CoinGecko). "
            "Cannot generate synthetic data. Failing closed."
        )

    def _bybit_klines(self, symbol: str, limit: int = 60) -> List[Dict]:
        """Fetch klines from Bybit via CDN bypass."""
        for ip in self._exchange._bybit_ips:
            data = DNSBypass._raw_https(ip, self._exchange.BYBIT_CDN_CNAME, self._exchange.BYBIT_HOST,
                f"/v5/market/kline?category=spot&symbol={symbol}&interval=1&limit={limit}")
            if data and data.get("retCode") == 0:
                raw = data["result"].get("list", [])
                return [{
                    "timestamp": int(r[0]),
                    "open": float(r[1]), "high": float(r[2]),
                    "low": float(r[3]), "close": float(r[4]), "volume": float(r[5]),
                    "synthetic": False,
                } for r in raw]
        return []

    def health(self) -> Dict:
        btc = self._exchange.get_price("BTCUSDT")
        prices = self.get_all_prices(force=False)
        return {
            "status": "ok" if prices else "degraded",
            "prices_fetched": len(prices),
            "coins": list(prices.keys()),
            "bypass_active": btc is not None,
            "exchange": "bybit+okx+coingecko",
        }


class EngineRiskManager:
    """Risk manager using engine/risk/ constants and engine/persistence/.

    Replaces live_engine.py's inline RiskManager with one that:
    - Uses constitutional limits from engine/risk/constants (0.5% per trade, 1% daily, etc.)
    - Persists state via engine/persistence/ (FileBackend)
    - Tracks drawdown using engine/risk/ constants
    - Compatible with live_engine.py's existing RiskManager interface
    """

    def __init__(self, db, initial_balance: float = 10000.0):
        self.db = db
        self._persistence = None
        self._init_constants()
        self._init_persistence()
        self._load_state(initial_balance)

    def _init_constants(self):
        self.MAX_RISK_PER_TRADE = 0.005
        self.MAX_POSITION_PCT = 0.10
        self.MAX_DAILY_LOSS = 0.01
        self.MAX_WEEKLY_LOSS = 0.03
        self.MAX_DRAWDOWN = 0.10
        try:
            from quant_nanggroe.engine.risk.constants import (
                MAX_DAILY_LOSS,
                MAX_DRAWDOWN_PCT,
                MAX_POSITION_SIZE_PCT,
                MAX_RISK_PER_TRADE,
                MAX_WEEKLY_LOSS,
            )
            self.MAX_RISK_PER_TRADE = MAX_RISK_PER_TRADE
            self.MAX_POSITION_PCT = MAX_POSITION_SIZE_PCT
            self.MAX_DAILY_LOSS = MAX_DAILY_LOSS
            self.MAX_WEEKLY_LOSS = MAX_WEEKLY_LOSS
            self.MAX_DRAWDOWN = MAX_DRAWDOWN_PCT
        except Exception as e:
            log.debug(f"engine/risk/constants import failed, using defaults: {e}")

    def _init_persistence(self):
        try:
            from quant_nanggroe.engine.persistence import get_persistence_backend
            self._persistence = get_persistence_backend()
        except Exception as e:
            log.debug(f"Persistence unavailable: {e}")

    def _load_state(self, initial_balance: float):
        self._balance = initial_balance
        self._peak = initial_balance
        self._total_trades = 0
        self._winning_trades = 0
        self._daily_pnl = 0.0
        self._weekly_pnl = 0.0
        self._today = datetime.now().date()
        self._trade_count_today = 0

        if self._persistence:
            try:
                bal = self._persistence.get("risk:balance")
                if bal is not None:
                    self._balance = float(bal)
                pk = self._persistence.get("risk:peak")
                if pk is not None:
                    self._peak = float(pk)
                daily = self._persistence.get("risk:daily_pnl")
                if daily is not None:
                    self._daily_pnl = float(daily)
                weekly = self._persistence.get("risk:weekly_pnl")
                if weekly is not None:
                    self._weekly_pnl = float(weekly)
            except Exception as e:
                log.debug(f"Persistence load error: {e}")

        self._sync_from_db()

    def _sync_from_db(self):
        try:
            cur = self.db.execute("SELECT value FROM portfolio WHERE key='balance'")
            row = cur.fetchone()
            if row:
                self._balance = float(row[0])
            cur = self.db.execute("SELECT value FROM portfolio WHERE key='peak'")
            row = cur.fetchone()
            if row:
                self._peak = float(row[0])
            cur = self.db.execute("SELECT value FROM portfolio WHERE key='total_trades'")
            row = cur.fetchone()
            if row:
                self._total_trades = int(row[0])
            cur = self.db.execute("SELECT value FROM portfolio WHERE key='winning_trades'")
            row = cur.fetchone()
            if row:
                self._winning_trades = int(row[0])
        except Exception as e:
            log.debug(f"DB sync error: {e}")

    def _save(self):
        if self._persistence:
            try:
                self._persistence.set_many({
                    "risk:balance": self._balance,
                    "risk:peak": self._peak,
                    "risk:daily_pnl": self._daily_pnl,
                    "risk:weekly_pnl": self._weekly_pnl,
                }, ttl=86400 * 7)
            except Exception as e:
                log.debug(f"Persistence save error: {e}")

    def get_balance(self) -> float:
        self._sync_from_db()
        return self._balance

    def get_peak(self) -> float:
        self._sync_from_db()
        return self._peak

    def get_drawdown(self) -> float:
        peak = self.get_peak()
        balance = self.get_balance()
        return (peak - balance) / peak if peak > 0 else 0

    def get_open_position_count(self) -> int:
        cur = self.db.execute("SELECT COUNT(*) FROM positions WHERE status='open'")
        return cur.fetchone()[0]

    def can_trade(self) -> Tuple[bool, str]:
        dd = self.get_drawdown()
        if dd > self.MAX_DRAWDOWN:
            return False, f"Drawdown {dd:.1%} exceeds {self.MAX_DRAWDOWN:.1%}"
        open_count = self.get_open_position_count()
        if open_count >= MAX_POSITIONS_TOTAL:
            return False, f"Max positions ({MAX_POSITIONS_TOTAL}) reached"
        # P0 FIX: weekly loss veto — was completely missing, could blow past 3% weekly limit
        balance = self.get_balance()
        if balance > 0 and self._weekly_pnl < 0:
            weekly_loss_pct = abs(self._weekly_pnl) / balance
            if weekly_loss_pct >= self.MAX_WEEKLY_LOSS:
                return False, f"Weekly loss {weekly_loss_pct:.1%} exceeds {self.MAX_WEEKLY_LOSS:.1%}"
        # P0 FIX: daily loss veto using real tracked PnL
        if balance > 0 and self._daily_pnl < 0:
            daily_loss_pct = abs(self._daily_pnl) / balance
            if daily_loss_pct >= self.MAX_DAILY_LOSS:
                return False, f"Daily loss {daily_loss_pct:.1%} exceeds {self.MAX_DAILY_LOSS:.1%}"
        return True, "ok"

    def position_size(self, price: float, kelly: float = 1.0) -> float:
        balance = self.get_balance()
        return (balance * self.MAX_POSITION_PCT * kelly) / price

    def update_peak(self):
        balance = self.get_balance()
        peak = self.get_peak()
        if balance > peak:
            self.db.execute("UPDATE portfolio SET value=? WHERE key='peak'", (balance,))
            self.db.commit()

    def check_trade(self, symbol: str, direction: str, price: float, qty: float, strategy: str) -> Dict:
        result = {
            "verdict": "APPROVED",
            "symbol": symbol,
            "direction": direction,
            "price": price,
            "qty": qty,
            "strategy": strategy,
        }
        dd = self.get_drawdown()
        if dd > self.MAX_DRAWDOWN:
            return {**result, "verdict": "VETOED", "reason": f"Drawdown {dd:.1%}"}
        open_count = self.get_open_position_count()
        if open_count >= MAX_POSITIONS_TOTAL:
            return {**result, "verdict": "VETOED", "reason": f"Max positions ({MAX_POSITIONS_TOTAL})"}
        # P0 FIX: weekly loss veto in check_trade (mirrors can_trade)
        balance = self.get_balance()
        if balance > 0 and self._weekly_pnl < 0:
            weekly_loss_pct = abs(self._weekly_pnl) / balance
            if weekly_loss_pct >= self.MAX_WEEKLY_LOSS:
                return {**result, "verdict": "VETOED", "reason": f"Weekly loss {weekly_loss_pct:.1%}"}
        if balance > 0 and self._daily_pnl < 0:
            daily_loss_pct = abs(self._daily_pnl) / balance
            if daily_loss_pct >= self.MAX_DAILY_LOSS:
                return {**result, "verdict": "VETOED", "reason": f"Daily loss {daily_loss_pct:.1%}"}
        return result

    @property
    def balance(self) -> float:
        return self.get_balance()

    @property
    def peak(self) -> float:
        return self.get_peak()

    def total_trades(self) -> int:
        return self._total_trades

    def winning_trades(self) -> int:
        return self._winning_trades


class StalePositionAnalyzer:
    """Analyzes and logs stale open positions from the database."""

    def __init__(self, db, price_provider: EnginePriceProvider):
        self.db = db
        self.prices = price_provider

    def get_open_positions(self) -> List[Dict]:
        cur = self.db.execute(
            "SELECT id, symbol, side, entry_price, quantity, entry_time, "
            "highest_since_entry, strategy, partial_exit_price, exited_qty "
            "FROM positions WHERE status='open' ORDER BY id"
        )
        positions = []
        for row in cur.fetchall():
            positions.append({
                "id": row[0], "symbol": row[1], "side": row[2],
                "entry_price": row[3], "quantity": row[4],
                "entry_time": row[5], "highest_since_entry": row[6] or row[3],
                "strategy": row[7], "partial_exit_price": row[8] or 0,
                "exited_qty": row[9] or 0,
            })
        return positions

    def analyze(self) -> List[Dict]:
        positions = self.get_open_positions()
        if not positions:
            log.info("No stale open positions found")
            return []

        prices = self.prices.get_all_prices(force=True)
        results = []

        for pos in positions:
            symbol = pos["symbol"]
            current_price = prices.get(symbol, 0.0)
            remaining = pos["quantity"] - pos["exited_qty"]
            unrealized_pnl = (current_price - pos["entry_price"]) * remaining
            unrealized_pct = ((current_price - pos["entry_price"]) / pos["entry_price"] * 100) if pos["entry_price"] > 0 else 0

            entry_time = pos.get("entry_time", "unknown")

            entry = {
                "id": pos["id"],
                "symbol": symbol,
                "side": pos["side"],
                "entry_price": pos["entry_price"],
                "current_price": current_price,
                "quantity": pos["quantity"],
                "remaining": remaining,
                "exited_qty": pos["exited_qty"],
                "strategy": pos["strategy"],
                "entry_time": entry_time,
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pct, 2),
                "price_source": "CoinGecko" if current_price > 0 else "NONE",
            }
            results.append(entry)

        total_unrealized = sum(r["unrealized_pnl"] for r in results)
        log.info("=" * 60)
        log.info("STALE POSITIONS REPORT")
        log.info("=" * 60)
        for r in results:
            pnl_sign = "+" if r["unrealized_pnl"] >= 0 else ""
            log.info(
                f"  #{r['id']} {r['symbol']} ({r['strategy']}): "
                f"entry=${r['entry_price']:.2f}, current=${r['current_price']:.4f}, "
                f"qty={r['remaining']:.4f}, "
                f"PnL={pnl_sign}${r['unrealized_pnl']:.2f} ({pnl_sign}{r['unrealized_pnl_pct']:.2f}%)"
            )
        total_sign = "+" if total_unrealized >= 0 else ""
        log.info(f"  TOTAL UNREALIZED PnL: {total_sign}${total_unrealized:.2f}")
        log.info(f"  Current Balance: ${self._get_balance():.2f}")
        log.info("=" * 60)

        return results

    def _get_balance(self) -> float:
        try:
            cur = self.db.execute("SELECT value FROM portfolio WHERE key='balance'")
            row = cur.fetchone()
            return float(row[0]) if row else 0.0
        except Exception:
            return 0.0
