# Coverage target: equity_engine.py, forex_engine.py, futures_engine.py, market_detection.py

from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.engines.equity_engine import EquityEngine
from quant_nanggroe.engine.backtest.engines.forex_engine import (
    ForexEngine,
    calc_forex_swap,
    _normalize_symbol,
    _pip_value,
    _SPREAD_PIPS,
)
from quant_nanggroe.engine.backtest.engines.futures_engine import (
    FuturesEngine,
    _extract_product,
    _CN_FUTURES_MULTIPLIERS,
    _GLOBAL_FUTURES_MULTIPLIERS,
)
from quant_nanggroe.engine.backtest.engines.market_detection import (
    detect_market,
    detect_submarket,
    is_china_futures,
)
from quant_nanggroe.engine.backtest.engines.base_engine import Position


class TestEquityEngine(unittest.TestCase):
    """Tests for EquityEngine — US / HK / China-A equity rules."""

    def test_init_defaults_us(self):
        eng = EquityEngine({"initial_cash": 500_000}, market="us")
        self.assertEqual(eng.market, "us")
        self.assertEqual(eng.initial_capital, 500_000)
        self.assertAlmostEqual(eng.slippage_us, 0.0005)
        self.assertEqual(eng.calc_commission(100, 150, 1, True), 0.0)

    def test_init_defaults_hk(self):
        eng = EquityEngine({"initial_cash": 1_000_000}, market="hk")
        self.assertEqual(eng.market, "hk")
        self.assertAlmostEqual(eng.slippage_hk, 0.001)

    def test_init_defaults_china_a(self):
        eng = EquityEngine({"initial_cash": 1_000_000}, market="china_a")
        self.assertEqual(eng.market, "china_a")
        self.assertAlmostEqual(eng.commission_rate, 0.00025)
        self.assertAlmostEqual(eng.commission_min, 5.0)

    def test_init_with_config_overrides(self):
        cfg = {
            "initial_cash": 2_000_000,
            "slippage_us": 0.001,
            "commission_rate": 0.0005,
            "commission_min": 10.0,
        }
        eng = EquityEngine(cfg, market="us")
        self.assertEqual(eng.initial_capital, 2_000_000)
        self.assertAlmostEqual(eng.slippage_us, 0.001)
        self.assertAlmostEqual(eng.commission_rate, 0.0005)
        self.assertAlmostEqual(eng.commission_min, 10.0)

    def test_can_execute_us_always_true(self):
        eng = EquityEngine({}, market="us")
        bar = pd.Series({"close": 100.0})
        self.assertTrue(eng.can_execute("AAPL", 1, bar))
        self.assertTrue(eng.can_execute("AAPL", -1, bar))
        self.assertTrue(eng.can_execute("AAPL", 0, bar))

    def test_can_execute_china_no_short(self):
        eng = EquityEngine({}, market="china_a")
        bar = pd.Series({"close": 100.0, "pct_chg": 0.5})
        self.assertFalse(eng.can_execute("000001.SZ", -1, bar))

    def test_can_execute_china_limit_up_blocks_buy(self):
        eng = EquityEngine({}, market="china_a")
        bar = pd.Series({"close": 110.0, "pre_close": 100.0, "pct_chg": 10.0})
        self.assertFalse(eng.can_execute("000001.SZ", 1, bar))

    def test_can_execute_china_limit_down_blocks_sell(self):
        eng = EquityEngine({}, market="china_a")
        bar = pd.Series({"close": 90.0, "pre_close": 100.0, "pct_chg": -10.0})
        self.assertFalse(eng.can_execute("000001.SZ", 0, bar))

    def test_can_execute_china_normal_trade(self):
        eng = EquityEngine({}, market="china_a")
        bar = pd.Series({"close": 105.0, "pre_close": 100.0, "pct_chg": 5.0})
        self.assertTrue(eng.can_execute("000001.SZ", 1, bar))

    def test_round_size_us_fractional(self):
        eng = EquityEngine({}, market="us")
        self.assertAlmostEqual(eng.round_size(100.456, 150.0), 100.46)
        self.assertAlmostEqual(eng.round_size(-10.0, 150.0), 0.0)

    def test_round_size_hk_lot(self):
        eng = EquityEngine({}, market="hk")
        self.assertEqual(eng.round_size(250.0, 100.0), 200.0)
        self.assertEqual(eng.round_size(49.0, 100.0), 0.0)

    def test_round_size_china_lot(self):
        eng = EquityEngine({}, market="china_a")
        self.assertEqual(eng.round_size(250.0, 100.0), 200.0)

    def test_calc_commission_us_zero(self):
        eng = EquityEngine({}, market="us")
        self.assertEqual(eng.calc_commission(100, 150, 1, True), 0.0)
        self.assertEqual(eng.calc_commission(100, 150, -1, False), 0.0)

    def test_calc_commission_hk(self):
        eng = EquityEngine({}, market="hk")
        comm = eng.calc_commission(100, 200, 1, True)
        notional = 100 * 200
        expected = notional * (0.00015 + 0.001 + 0.0000565 + 0.00002)
        self.assertAlmostEqual(comm, expected)

    def test_calc_commission_china_open(self):
        eng = EquityEngine({}, market="china_a")
        comm = eng.calc_commission(100, 50, 1, True)
        notional = 100 * 50
        expected = max(notional * 0.00025, 5.0) + notional * 0.00001
        self.assertAlmostEqual(comm, expected)

    def test_calc_commission_china_close_includes_stamp(self):
        eng = EquityEngine({}, market="china_a")
        comm = eng.calc_commission(100, 50, 1, False)
        notional = 100 * 50
        expected = max(notional * 0.00025, 5.0) + notional * 0.00001 + notional * 0.0005
        self.assertAlmostEqual(comm, expected)

    def test_apply_slippage_us(self):
        eng = EquityEngine({}, market="us")
        self.assertAlmostEqual(eng.apply_slippage(100.0, 1), 100.0 * 1.0005)
        self.assertAlmostEqual(eng.apply_slippage(100.0, -1), 100.0 * 0.9995)

    def test_apply_slippage_hk(self):
        eng = EquityEngine({}, market="hk")
        self.assertAlmostEqual(eng.apply_slippage(100.0, 1), 100.0 * 1.001)

    def test_apply_slippage_china(self):
        eng = EquityEngine({}, market="china_a")
        self.assertAlmostEqual(eng.apply_slippage(100.0, 1), 100.0 * 1.001)

    def test_calc_pnl_long(self):
        eng = EquityEngine({}, market="us")
        pnl = eng._calc_pnl("AAPL", 1, 100, 100.0, 110.0)
        self.assertAlmostEqual(pnl, 1000.0)

    def test_calc_pnl_short(self):
        eng = EquityEngine({}, market="us")
        pnl = eng._calc_pnl("AAPL", -1, 100, 110.0, 100.0)
        self.assertAlmostEqual(pnl, 1000.0)

    def test_on_bar_noop(self):
        eng = EquityEngine({}, market="us")
        bar = pd.Series({"close": 100.0})
        ts = pd.Timestamp("2024-01-02")
        capital_before = eng.capital
        eng.on_bar("AAPL", bar, ts)
        self.assertEqual(eng.capital, capital_before)


class TestForexEngine(unittest.TestCase):
    """Tests for ForexEngine — FX spot/CFD rules."""

    def test_init_defaults(self):
        eng = ForexEngine({})
        self.assertAlmostEqual(eng.default_leverage, 100.0)
        self.assertEqual(eng.lot_size, 100_000)
        self.assertTrue(eng.swap_enabled)
        self.assertAlmostEqual(eng.slippage_pips, 0.3)

    def test_init_with_config(self):
        eng = ForexEngine({
            "initial_cash": 50_000,
            "leverage": 200.0,
            "lot_size": 10_000,
            "swap_enabled": False,
            "slippage_pips": 0.5,
        })
        self.assertEqual(eng.initial_capital, 50_000)
        self.assertAlmostEqual(eng.default_leverage, 200.0)
        self.assertEqual(eng.lot_size, 10_000)
        self.assertFalse(eng.swap_enabled)
        self.assertAlmostEqual(eng.slippage_pips, 0.5)

    def test_can_execute_always_true(self):
        eng = ForexEngine({})
        bar = pd.Series({"close": 1.1000})
        self.assertTrue(eng.can_execute("EUR/USD", 1, bar))
        self.assertTrue(eng.can_execute("EUR/USD", -1, bar))
        self.assertTrue(eng.can_execute("EUR/USD", 0, bar))

    def test_round_size(self):
        eng = ForexEngine({})
        self.assertEqual(eng.round_size(150_000, 1.1000), 150_000)
        self.assertEqual(eng.round_size(151_500, 1.1000), 151_000)
        self.assertEqual(eng.round_size(500, 1.1000), 0)

    def test_calc_commission_zero(self):
        eng = ForexEngine({})
        self.assertEqual(eng.calc_commission(100_000, 1.1000, 1, True), 0.0)
        self.assertEqual(eng.calc_commission(100_000, 1.1000, -1, False), 0.0)

    def test_apply_slippage_buy_default_spread(self):
        eng = ForexEngine({})
        price = 1.1000
        eng._active_symbol = "EUR/USD"
        pip = _pip_value("EUR/USD")
        spread_pips = _SPREAD_PIPS.get("EUR/USD", 2.0)
        total_pips = (spread_pips / 2) + eng.slippage_pips
        expected = price + 1 * total_pips * pip
        self.assertAlmostEqual(eng.apply_slippage(price, 1), expected)

    def test_apply_slippage_sell_default_spread(self):
        eng = ForexEngine({})
        price = 1.1000
        eng._active_symbol = "EUR/USD"
        pip = _pip_value("EUR/USD")
        spread_pips = _SPREAD_PIPS.get("EUR/USD", 2.0)
        total_pips = (spread_pips / 2) + eng.slippage_pips
        expected = price - 1 * total_pips * pip
        self.assertAlmostEqual(eng.apply_slippage(price, -1), expected)

    def test_apply_slippage_jpy_pair(self):
        eng = ForexEngine({})
        price = 150.00
        eng._active_symbol = "USD/JPY"
        result = eng.apply_slippage(price, 1)
        pip = _pip_value("USD/JPY")
        spread_pips = _SPREAD_PIPS.get("USD/JPY", 2.0)
        total_pips = (spread_pips / 2) + eng.slippage_pips
        expected = price + 1 * total_pips * pip
        self.assertAlmostEqual(result, expected)

    def test_apply_slippage_override_spread(self):
        eng = ForexEngine({"spread_pips_override": 5.0})
        price = 1.1000
        eng._active_symbol = "EUR/USD"
        pip = _pip_value("EUR/USD")
        total_pips = (5.0 / 2) + eng.slippage_pips
        expected = price + 1 * total_pips * pip
        self.assertAlmostEqual(eng.apply_slippage(price, 1), expected)

    def test_apply_slippage_for_symbol_direct(self):
        eng = ForexEngine({})
        result = eng.apply_slippage_for_symbol("GBP/USD", 1.2500, 1)
        pip = _pip_value("GBP/USD")
        spread_pips = _SPREAD_PIPS.get("GBP/USD", 2.0)
        total_pips = (spread_pips / 2) + eng.slippage_pips
        expected = 1.2500 + 1 * total_pips * pip
        self.assertAlmostEqual(result, expected)

    def test_swap_calculated_wednesday_triple(self):
        pos = {
            "EUR/USD": Position(
                symbol="EUR/USD", direction=1, entry_price=1.10,
                entry_time=pd.Timestamp("2024-01-01"), size=100_000,
            )
        }
        ts = pd.Timestamp("2024-01-03")  # Wednesday
        swap = calc_forex_swap("EUR/USD", ts, pos, 100_000, {})
        self.assertEqual(swap, 1.0 * (-6.5) * 3.0)

    def test_swap_only_once_per_day(self):
        pos = {
            "EUR/USD": Position(
                symbol="EUR/USD", direction=1, entry_price=1.10,
                entry_time=pd.Timestamp("2024-01-01"), size=100_000,
            )
        }
        last_dates = {}
        ts = pd.Timestamp("2024-01-02")
        swap1 = calc_forex_swap("EUR/USD", ts, pos, 100_000, last_dates)
        swap2 = calc_forex_swap("EUR/USD", ts, pos, 100_000, last_dates)
        self.assertNotEqual(swap1, 0.0)
        self.assertEqual(swap2, 0.0)

    def test_swap_zero_no_position(self):
        ts = pd.Timestamp("2024-01-02")
        swap = calc_forex_swap("EUR/USD", ts, {}, 100_000, {})
        self.assertEqual(swap, 0.0)

    def test_on_bar_swap_applied(self):
        eng = ForexEngine({"initial_cash": 1_000_000})
        eng.positions["EUR/USD"] = Position(
            symbol="EUR/USD", direction=1, entry_price=1.10,
            entry_time=pd.Timestamp("2024-01-01"), size=100_000,
        )
        bar = pd.Series({"close": 1.10})
        ts = pd.Timestamp("2024-01-02")
        cap_before = eng.capital
        eng.on_bar("EUR/USD", bar, ts)
        self.assertNotEqual(eng.capital, cap_before)

    def test_on_bar_swap_disabled(self):
        eng = ForexEngine({"initial_cash": 1_000_000, "swap_enabled": False})
        eng.positions["EUR/USD"] = Position(
            symbol="EUR/USD", direction=1, entry_price=1.10,
            entry_time=pd.Timestamp("2024-01-01"), size=100_000,
        )
        bar = pd.Series({"close": 1.10})
        ts = pd.Timestamp("2024-01-02")
        cap_before = eng.capital
        eng.on_bar("EUR/USD", bar, ts)
        self.assertEqual(eng.capital, cap_before)

    def test_get_contract_multiplier(self):
        eng = ForexEngine({})
        self.assertEqual(eng.get_contract_multiplier("EUR/USD"), 1.0)

    def test_reset_state_clears_swap_dates(self):
        eng = ForexEngine({})
        eng._last_swap_dates["EUR/USD"] = pd.Timestamp("2024-01-02").date()
        eng._reset_state()
        self.assertEqual(eng._last_swap_dates, {})


class TestFuturesEngine(unittest.TestCase):
    """Tests for FuturesEngine — contract multiplier, margin, commissions."""

    def test_init_defaults(self):
        eng = FuturesEngine({})
        self.assertAlmostEqual(eng.default_leverage, 10.0)
        self.assertAlmostEqual(eng.commission_per_contract, 0.0)
        self.assertAlmostEqual(eng.commission_rate, 0.00005)
        self.assertAlmostEqual(eng.slippage_rate, 0.0003)
        self.assertAlmostEqual(eng.margin_rate, 0.1)

    def test_init_with_config(self):
        eng = FuturesEngine({
            "initial_cash": 5_000_000,
            "leverage": 20.0,
            "commission_per_contract": 3.0,
            "commission_rate": 0.0001,
            "slippage": 0.0005,
            "margin_rate": 0.05,
        })
        self.assertEqual(eng.initial_capital, 5_000_000)
        self.assertAlmostEqual(eng.default_leverage, 20.0)
        self.assertAlmostEqual(eng.commission_per_contract, 3.0)
        self.assertAlmostEqual(eng.commission_rate, 0.0001)
        self.assertAlmostEqual(eng.slippage_rate, 0.0005)
        self.assertAlmostEqual(eng.margin_rate, 0.05)

    def test_can_execute_always_true(self):
        eng = FuturesEngine({})
        bar = pd.Series({"close": 5000.0})
        self.assertTrue(eng.can_execute("ESZ4", 1, bar))
        self.assertTrue(eng.can_execute("ESZ4", -1, bar))
        self.assertTrue(eng.can_execute("ESZ4", 0, bar))

    def test_round_size_integer_contracts(self):
        eng = FuturesEngine({})
        self.assertEqual(eng.round_size(5.7, 5000.0), 5)
        self.assertEqual(eng.round_size(0.4, 5000.0), 0)
        self.assertEqual(eng.round_size(-3.0, 5000.0), 0)

    def test_calc_commission_per_contract_only(self):
        eng = FuturesEngine({"commission_per_contract": 2.50, "commission_rate": 0.0})
        eng._active_symbol = "ES2024"
        comm = eng.calc_commission(10, 5000.0, 1, True)
        self.assertAlmostEqual(comm, 10 * 2.50)

    def test_calc_commission_rate_based(self):
        eng = FuturesEngine({"commission_per_contract": 0.0, "commission_rate": 0.0001})
        eng._active_symbol = "ES2024"
        cm = eng.get_contract_multiplier("ES2024")
        notional = 10 * 5000.0 * cm
        expected = notional * 0.0001
        self.assertAlmostEqual(eng.calc_commission(10, 5000.0, 1, True), expected)

    def test_calc_commission_both(self):
        eng = FuturesEngine({"commission_per_contract": 1.0, "commission_rate": 0.00005})
        eng._active_symbol = "ES2024"
        cm = eng.get_contract_multiplier("ES2024")
        notional = 10 * 5000.0 * cm
        expected = 10 * 1.0 + notional * 0.00005
        self.assertAlmostEqual(eng.calc_commission(10, 5000.0, 1, True), expected)

    def test_apply_slippage(self):
        eng = FuturesEngine({})
        self.assertAlmostEqual(eng.apply_slippage(5000.0, 1), 5000.0 * 1.0003)
        self.assertAlmostEqual(eng.apply_slippage(5000.0, -1), 5000.0 * 0.9997)

    def test_calc_pnl_with_multiplier(self):
        eng = FuturesEngine({})
        pnl = eng._calc_pnl("IF2406.CFFEX", 1, 10, 5000.0, 5100.0)
        cm = eng.get_contract_multiplier("IF2406.CFFEX")
        expected = 1 * 10 * cm * (5100.0 - 5000.0)
        self.assertAlmostEqual(pnl, expected)

    def test_calc_pnl_short(self):
        eng = FuturesEngine({})
        pnl = eng._calc_pnl("IF2406.CFFEX", -1, 10, 5100.0, 5000.0)
        cm = eng.get_contract_multiplier("IF2406.CFFEX")
        expected = -1 * 10 * cm * (5000.0 - 5100.0)
        self.assertAlmostEqual(pnl, expected)

    def test_calc_margin(self):
        eng = FuturesEngine({})
        margin = eng._calc_margin("IF2406.CFFEX", 10, 5000.0, 10.0)
        cm = eng.get_contract_multiplier("IF2406.CFFEX")
        expected = 10 * 5000.0 * cm / 10.0
        self.assertAlmostEqual(margin, expected)

    def test_calc_raw_size(self):
        eng = FuturesEngine({})
        raw = eng._calc_raw_size("IF2406.CFFEX", 250_000, 5000.0)
        cm = eng.get_contract_multiplier("IF2406.CFFEX")
        expected = 250_000 / (5000.0 * cm)
        self.assertAlmostEqual(raw, expected)

    def test_get_contract_multiplier_cn_futures(self):
        eng = FuturesEngine({})
        self.assertEqual(eng.get_contract_multiplier("IF2406.CFFEX"), 300)
        self.assertEqual(eng.get_contract_multiplier("rb2410.SHFE"), 10)

    def test_get_contract_multiplier_global_futures(self):
        eng = FuturesEngine({})
        self.assertEqual(eng.get_contract_multiplier("ES2024"), 50)
        self.assertEqual(eng.get_contract_multiplier("CL2025"), 1000)

    def test_get_contract_multiplier_unknown_default(self):
        eng = FuturesEngine({})
        self.assertEqual(eng.get_contract_multiplier("ZZ9999"), 1.0)

    def test_get_contract_multiplier_custom_override(self):
        eng = FuturesEngine({"multipliers": {"ESZ4": 100}})
        self.assertEqual(eng.get_contract_multiplier("ESZ4"), 100)

    def test_get_contract_multiplier_cache(self):
        eng = FuturesEngine({})
        eng.get_contract_multiplier("IF2406.CFFEX")
        eng.get_contract_multiplier("IF2406.CFFEX")
        self.assertIn("IF2406.CFFEX", eng._multiplier_cache)

    def test_on_bar_noop(self):
        eng = FuturesEngine({})
        bar = pd.Series({"close": 5000.0})
        ts = pd.Timestamp("2024-01-02")
        cap_before = eng.capital
        eng.on_bar("IF2406.CFFEX", bar, ts)
        self.assertEqual(eng.capital, cap_before)


class TestMarketDetection(unittest.TestCase):
    """Tests for market_detection — symbol classification and routing."""

    def test_detect_us_equity(self):
        self.assertEqual(detect_market("AAPL.US"), "us_equity")

    def test_detect_hk_equity(self):
        self.assertEqual(detect_market("00700.HK"), "hk_equity")

    def test_detect_a_share(self):
        self.assertEqual(detect_market("000001.SZ"), "a_share")
        self.assertEqual(detect_market("600000.SH"), "a_share")
        self.assertEqual(detect_market("300001.SZ"), "a_share")

    def test_detect_crypto_usdt_slash(self):
        self.assertEqual(detect_market("BTC/USDT"), "crypto")

    def test_detect_crypto_usdt_hyphen(self):
        self.assertEqual(detect_market("BTC-USDT"), "crypto")

    def test_detect_forex_pair(self):
        self.assertEqual(detect_market("EUR/USD"), "forex")
        self.assertEqual(detect_market("GBP/USD"), "forex")

    def test_detect_forex_fx_format(self):
        self.assertEqual(detect_market("EURUSD.FX"), "forex")

    def test_detect_china_futures(self):
        self.assertEqual(detect_market("IF2406.CFFEX"), "futures")
        self.assertEqual(detect_market("rb2410.SHFE"), "futures")

    def test_detect_global_futures(self):
        self.assertEqual(detect_market("ESZ4"), "futures")
        self.assertEqual(detect_market("CL2412"), "futures")

    def test_detect_unknown_defaults_to_us(self):
        self.assertEqual(detect_market("SOMETHING"), "us_equity")

    def test_is_china_futures_by_exchange(self):
        self.assertTrue(is_china_futures("IF2406.CFFEX"))
        self.assertTrue(is_china_futures("rb2410.SHFE"))

    def test_is_china_futures_by_product(self):
        self.assertTrue(is_china_futures("IF2406"))
        self.assertFalse(is_china_futures("ESZ4"))

    def test_is_china_futures_false_for_global(self):
        self.assertFalse(is_china_futures("ESZ4"))
        self.assertFalse(is_china_futures("CLF25"))

    def test_detect_submarket_hk(self):
        self.assertEqual(detect_submarket(["00700.HK", "00941.HK"]), "hk")

    def test_detect_submarket_china(self):
        self.assertEqual(detect_submarket(["000001.SZ"]), "china_a")

    def test_detect_submarket_default_us(self):
        self.assertEqual(detect_submarket(["AAPL.US", "MSFT.US"]), "us")

    def test_extract_product_with_exchange(self):
        self.assertEqual(_extract_product("IF2406.CFFEX"), "IF")
        self.assertEqual(_extract_product("rb2410.SHFE"), "RB")

    def test_extract_product_year_month_format(self):
        self.assertEqual(_extract_product("IF2406.CFFEX"), "IF")
        self.assertEqual(_extract_product("CL2412"), "CL")

    def test_extract_product_yyyymm_format(self):
        self.assertEqual(_extract_product("CL2412"), "CL")

    def test_pip_value_non_jpy(self):
        self.assertEqual(_pip_value("EUR/USD"), 0.0001)

    def test_pip_value_jpy(self):
        self.assertEqual(_pip_value("USD/JPY"), 0.01)

    def test_normalize_symbol_slash(self):
        self.assertEqual(_normalize_symbol("eur/usd"), "EUR/USD")

    def test_normalize_symbol_compact(self):
        self.assertEqual(_normalize_symbol("EURUSD"), "EUR/USD")

    def test_normalize_symbol_fx_format(self):
        self.assertEqual(_normalize_symbol("EURUSD.FX"), "EUR/USD")


if __name__ == "__main__":
    unittest.main()
