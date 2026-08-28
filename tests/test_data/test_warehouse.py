"""Tests for the Parquet-based data warehouse."""

from __future__ import annotations

import tempfile

from quant_nanggroe.data.warehouse import DataWarehouse
from quant_nanggroe.engine.monitor_hub import MetricSnapshot


def _make_cycle(cycle: int, ts: str | None = None) -> dict:
    return {
        "timestamp": ts or f"2024-01-{cycle:02d}T00:00:00",
        "cycle": cycle,
        "equity": 10000.0 + cycle * 100,
        "cash": 5000.0 + cycle * 50,
        "total_value": 10000.0 + cycle * 100,
        "unrealized_pnl": 100.0 - cycle * 10,
        "realized_pnl": 50.0 + cycle * 10,
        "drawdown_pct": float(cycle * 0.5),
        "regime": "bull" if cycle % 2 == 0 else "bear",
        "positions": 3 - (cycle % 3),
        "error_rate": float(cycle * 0.01),
    }


def _make_attribution(cycle: int, symbol: str = "BTC/USDT") -> dict:
    return {
        "timestamp": f"2024-01-{cycle:02d}T00:00:00",
        "cycle": cycle,
        "symbol": symbol,
        "strategy": "RegimeBased",
        "unrealized_pnl": 50.0,
        "realized_pnl": 25.0,
        "entry_price": 67000.0,
        "current_price": 67500.0,
        "position_qty": 0.1,
        "regime_at_entry": "bull",
    }


class TestDataWarehouse:
    def test_write_and_read_cycles(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            wh.write_cycle(_make_cycle(1))
            wh.write_cycle(_make_cycle(2))
            wh.write_cycle(_make_cycle(3))

            df = wh.query("cycles")
            assert len(df) == 3
            assert list(df.columns) == [
                "timestamp", "cycle_number", "equity", "cash", "total_value",
                "unrealized_pnl", "realized_pnl", "drawdown_pct", "regime",
                "num_positions", "error_rate",
            ]
            assert df.iloc[0]["cycle_number"] == 1
            assert df.iloc[2]["cycle_number"] == 3
            wh.close()

    def test_write_and_read_attribution(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            rows = [_make_attribution(1), _make_attribution(2, symbol="ETH/USDT")]
            wh.write_attribution(rows)

            df = wh.query("attribution")
            assert len(df) == 2
            assert df.iloc[0]["symbol"] == "BTC/USDT"
            assert df.iloc[1]["symbol"] == "ETH/USDT"
            wh.close()

    def test_write_and_read_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            snap = MetricSnapshot(
                execution_latency_ms=12.5,
                error_rate=0.01,
                signal_freshness_sec=5.0,
                pnl_per_cycle=100.0,
                risk_score=0.3,
                correlation=0.15,
                system_health=1.0,
                cycle_count=1,
                timestamp="2024-01-01T00:00:00",
            )
            wh.write_metrics(snap)

            df = wh.query("metrics")
            assert len(df) == 1
            assert df.iloc[0]["execution_latency_ms"] == 12.5
            assert df.iloc[0]["cycle_number"] == 1
            wh.close()

    def test_write_and_read_regimes(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            wh.write_regime({
                "detected_at": "2024-01-01T00:00:00",
                "cycle_number": 1,
                "regime": "bull_trend",
                "confidence": 0.75,
                "risk_multiplier": 1.0,
            })

            df = wh.query("regimes")
            assert len(df) == 1
            assert df.iloc[0]["regime"] == "bull_trend"
            assert df.iloc[0]["confidence"] == 0.75
            wh.close()

    def test_write_and_read_positions(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            wh.write_positions([
                {
                    "timestamp": "2024-01-01T00:00:00",
                    "cycle_number": 1,
                    "symbol": "BTC/USDT",
                    "side": "long",
                    "qty": 0.1,
                    "entry_price": 67000.0,
                    "current_price": 67500.0,
                    "unrealized_pnl": 50.0,
                }
            ])

            df = wh.query("positions")
            assert len(df) == 1
            assert df.iloc[0]["symbol"] == "BTC/USDT"
            assert df.iloc[0]["qty"] == 0.1
            wh.close()

    def test_query_filtering(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            for i in range(5):
                wh.write_cycle(_make_cycle(i + 1, ts=f"2024-01-{i+1:02d}T00:00:00"))

            df_all = wh.query("cycles")
            assert len(df_all) == 5

            df_since = wh.query("cycles", start_date="2024-01-03T00:00:00")
            assert len(df_since) == 3

            df_range = wh.query("cycles", start_date="2024-01-02T00:00:00",
                                 end_date="2024-01-04T00:00:00")
            assert len(df_range) == 3
            wh.close()

    def test_query_filtering_by_symbols(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            wh.write_attribution([
                _make_attribution(1, symbol="BTC/USDT"),
                _make_attribution(2, symbol="ETH/USDT"),
                _make_attribution(3, symbol="SOL/USDT"),
            ])

            df = wh.query("attribution", symbols=["BTC/USDT", "ETH/USDT"])
            assert len(df) == 2
            assert set(df["symbol"].tolist()) == {"BTC/USDT", "ETH/USDT"}
            wh.close()

    def test_summary_stats(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            wh.write_cycle(_make_cycle(1))
            wh.write_attribution([_make_attribution(1)])

            s = wh.summary()
            assert s["cycles"]["rows"] == 1
            assert s["attribution"]["rows"] == 1
            assert s["metrics"]["rows"] == 0
            assert s["regimes"]["rows"] == 0
            assert s["positions"]["rows"] == 0
            assert s["cycles"]["start"] is not None
            assert s["cycles"]["end"] is not None
            assert s["cycles"]["size_bytes"] > 0
            wh.close()

    def test_roundtrip_data_integrity(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            original = _make_cycle(5)
            wh.write_cycle(original)

            df = wh.query("cycles")
            assert len(df) == 1
            row = df.iloc[0]
            assert row["cycle_number"] == 5
            assert row["equity"] == 10500.0
            assert row["cash"] == 5250.0
            assert abs(row["drawdown_pct"] - 2.5) < 0.001
            assert row["regime"] == "bear"
            assert row["num_positions"] == 1
            wh.close()

    def test_empty_table(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            df = wh.query("cycles")
            assert df.empty
            wh.close()

    def test_attribution_empty(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            wh.write_attribution([])
            df = wh.query("attribution")
            assert df.empty
            wh.close()

    def test_positions_empty(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            wh.write_positions([])
            df = wh.query("positions")
            assert df.empty
            wh.close()

    def test_close_noop(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            wh.write_cycle(_make_cycle(1))
            wh.close()
            # Should not raise — close is a no-op
            assert True

    def test_write_metrics_with_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            wh = DataWarehouse(td)
            snap = MetricSnapshot()
            snap.cycle_count = 1
            snap.execution_latency_ms = 5.0
            snap.error_rate = 0.0
            snap.signal_freshness_sec = 2.0
            snap.pnl_per_cycle = 50.0
            snap.risk_score = 0.2
            snap.correlation = 0.1
            snap.system_health = 1.0
            snap.timestamp = "2024-01-01T00:00:00"

            wh.write_metrics(snap)
            df = wh.query("metrics")
            assert len(df) == 1
            assert df.iloc[0]["execution_latency_ms"] == 5.0
            wh.close()
