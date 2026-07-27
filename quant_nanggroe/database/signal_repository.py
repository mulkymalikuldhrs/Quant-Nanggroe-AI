"""
Trading Signal Repository — unified persistence layer for QNA signals.

Replaces ad-hoc JSON file persistence in autonomous.py and trade_lifecycle.py.
Provides CRUD + migration helpers so existing JSON stores can be imported
without data loss.

Usage:
    from quant_nanggroe.database.signal_repository import SignalRepository
    repo = SignalRepository()
    repo.save(signal_id="...", symbol="EURUSD", strategy_name="SMCv3", ...)
    pending = repo.list_pending()
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from quant_nanggroe.database.models import Base, TradingSignal

# ── Default DB path (same as models.py) ──────────────────────────────────
_DEFAULT_DB_URL = "sqlite:///data/agentic.db"


class SignalRepository:
    """CRUD for TradingSignal records with migration helpers."""

    def __init__(self, db_url: str | None = None) -> None:
        self._url = db_url or _DEFAULT_DB_URL
        self._engine = create_engine(self._url, echo=False)
        self._Session = sessionmaker(bind=self._engine)

    # ── Session context ──────────────────────────────────────────────────

    def _session(self) -> Session:
        return self._Session()

    # ── CRUD ─────────────────────────────────────────────────────────────

    def save(
        self,
        *,
        signal_id: str | None = None,
        symbol: str,
        strategy_name: str,
        signal_type: str,
        confidence: float = 0.0,
        price: float = 0.0,
        reason: str | None = None,
        exit_price: float | None = None,
        pnl_pct: float | None = None,
        is_win: bool | None = None,
        duration_seconds: int | None = None,
        provider: str | None = None,
        lifecycle_id: str | None = None,
        regime: str | None = None,
        evaluated_at: datetime | None = None,
    ) -> TradingSignal:
        """Create or update a signal record (upsert by signal_id)."""
        sid = signal_id or str(uuid.uuid4())
        record = TradingSignal(
            signal_id=sid,
            symbol=symbol,
            strategy_name=strategy_name,
            signal_type=signal_type,
            confidence=confidence,
            price=price,
            reason=reason,
            exit_price=exit_price,
            pnl_pct=pnl_pct,
            is_win=int(is_win) if is_win is not None else None,
            duration_seconds=duration_seconds,
            provider=provider,
            lifecycle_id=lifecycle_id,
            regime=regime,
            created_at=datetime.now(timezone.utc),
            evaluated_at=evaluated_at,
        )
        session = self._session()
        try:
            existing = session.query(TradingSignal).filter(
                TradingSignal.signal_id == sid
            ).first()
            if existing:
                for col in (
                    "symbol", "strategy_name", "signal_type", "confidence",
                    "price", "reason", "exit_price", "pnl_pct", "is_win",
                    "duration_seconds", "provider", "lifecycle_id", "regime",
                    "evaluated_at",
                ):
                    val = getattr(record, col, None)
                    if val is not None:
                        setattr(existing, col, val)
                session.commit()
                session.refresh(existing)
                return existing
            session.add(record)
            session.commit()
            session.refresh(record)
            return record
        finally:
            session.close()

    def get(self, signal_id: str) -> TradingSignal | None:
        """Fetch a single signal by ID."""
        session = self._session()
        try:
            return session.query(TradingSignal).filter(
                TradingSignal.signal_id == signal_id
            ).first()
        finally:
            session.close()

    def list(
        self,
        symbol: str | None = None,
        strategy_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TradingSignal]:
        """List signals with optional filters, newest first."""
        session = self._session()
        try:
            q = session.query(TradingSignal)
            if symbol:
                q = q.filter(TradingSignal.symbol == symbol)
            if strategy_name:
                q = q.filter(TradingSignal.strategy_name == strategy_name)
            return (
                q.order_by(TradingSignal.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
        finally:
            session.close()

    def list_pending(self, symbol: str | None = None) -> list[TradingSignal]:
        """List signals awaiting evaluation (is_win IS NULL)."""
        session = self._session()
        try:
            q = session.query(TradingSignal).filter(
                TradingSignal.is_win.is_(None)
            )
            if symbol:
                q = q.filter(TradingSignal.symbol == symbol)
            return q.order_by(TradingSignal.created_at.desc()).all()
        finally:
            session.close()

    def evaluate(
        self,
        signal_id: str,
        exit_price: float,
        pnl_pct: float,
        is_win: bool,
        duration_seconds: int | None = None,
    ) -> TradingSignal | None:
        """Mark a pending signal as evaluated."""
        session = self._session()
        try:
            record = session.query(TradingSignal).filter(
                TradingSignal.signal_id == signal_id
            ).first()
            if not record:
                return None
            record.exit_price = exit_price
            record.pnl_pct = pnl_pct
            record.is_win = int(is_win)
            record.duration_seconds = duration_seconds
            record.evaluated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(record)
            return record
        finally:
            session.close()

    def count(self, symbol: str | None = None) -> int:
        """Count total signals, optional symbol filter."""
        session = self._session()
        try:
            q = session.query(TradingSignal)
            if symbol:
                q = q.filter(TradingSignal.symbol == symbol)
            return q.count()
        finally:
            session.close()

    # ── Migration helpers ────────────────────────────────────────────────

    def import_from_json(
        self, json_path: str | Path, provider: str = "legacy_json"
    ) -> int:
        """Import signals from a legacy JSON file (e.g. data/strategy_signals.json).
        
        Returns number of records imported.
        Returns -1 if file not found.
        """
        path = Path(json_path)
        if not path.exists():
            return -1

        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return 0

        imported = 0
        for item in raw:
            sig_type = item.get("signal", item.get("signal_type", "hold"))
            if sig_type == "hold" and not item.get("price"):
                continue  # skip no-op entries
            self.save(
                signal_id=item.get("id") or item.get("signal_id"),
                symbol=item.get("symbol", "UNKNOWN"),
                strategy_name=item.get("strategy", item.get("strategy_name", "unknown")),
                signal_type=sig_type,
                confidence=float(item.get("confidence", 0)),
                price=float(item.get("price", 0)),
                reason=item.get("reason"),
                exit_price=item.get("exit_price") or item.get("close_price"),
                pnl_pct=item.get("pnl_pct"),
                is_win=item.get("is_win"),
                provider=provider,
            )
            imported += 1
        return imported

    def create_table(self) -> None:
        """Create the trading_signals table if it does not exist."""
        Base.metadata.create_all(self._engine, tables=[TradingSignal.__table__])


# ── Convenience singleton ────────────────────────────────────────────────
_default_repo: SignalRepository | None = None


def get_signal_repo(db_url: str | None = None) -> SignalRepository:
    """Get the default signal repository (lazy singleton)."""
    global _default_repo
    if _default_repo is None:
        _default_repo = SignalRepository(db_url=db_url)
        _default_repo.create_table()
    return _default_repo
