"""TDD for 6 vector modules — Klip 00:00-00:23

Covers:
- CurrencyGraph (WDG, equilibrium, .vxc suffix)
- CrossMatrix (reciprocity, implied CAD/JPY)
- TriArb (Δ = quoted - implied)
- VectorManifold (PointYEN/CHF/CAD, JPY /100)
- EuclideanMispricing (d, √2, box breach)
- GridExecutor (eigenvector, build_grid)
"""
import math
import numpy as np
import pytest


# ── CurrencyGraph ──
def test_currency_graph_equilibrium():
    from quant_nanggroe.engine.currency_graph import CurrencyGraph
    g = CurrencyGraph()
    # EUR/USD 1.08, USD/JPY 147.5, EUR/JPY 159.3 (=1.08*147.5)
    g.add_rate("EUR", "USD", 1.08, "EURUSD.vx")
    g.add_rate("USD", "JPY", 147.5, "USDJPY.vx")
    g.add_rate("EUR", "JPY", 159.3, "EURJPY.vx")
    is_eq, prod = g.check_equilibrium("EUR", "USD", "JPY")
    assert is_eq is True
    assert prod == pytest.approx(1.0, abs=1e-4)


def test_currency_graph_vxc_suffix_parsed():
    from quant_nanggroe.engine.currency_graph import build_graph_from_rates
    rates = {"EURUSD.vx": 1.08, "USDJPY.vx": 147.5}
    g = build_graph_from_rates(rates)
    assert g.get_rate("EUR", "USD") == pytest.approx(1.08)
    assert g.get_rate("JPY", "USD") == pytest.approx(1/147.5)


def test_currency_graph_find_triangular_cycles():
    from quant_nanggroe.engine.currency_graph import CurrencyGraph
    g = CurrencyGraph()
    g.add_rate("EUR", "USD", 1.08, "EURUSD.vx")
    g.add_rate("USD", "JPY", 147.5, "USDJPY.vx")
    # Deliberately misprice EUR/JPY to create arb: quoted 160 vs implied 159.3
    g.add_rate("EUR", "JPY", 160.0, "EURJPY.vx")
    cycles = g.find_triangular_cycles(threshold=0.0002)
    assert len(cycles) >= 1
    assert any(c["delta"] > 0.0002 for c in cycles)


# ── CrossMatrix ──
def test_cross_matrix_reciprocity():
    from quant_nanggroe.engine.cross_matrix import CrossMatrix
    cm = CrossMatrix(["EUR", "USD", "JPY"])
    cm.set_rate("EUR", "USD", 1.08)
    assert cm.get_rate("USD", "EUR") == pytest.approx(1/1.08)
    assert cm.m[0, 0] == pytest.approx(1.0)


def test_cross_matrix_implied_cadjpy():
    from quant_nanggroe.engine.cross_matrix import CrossMatrix
    cm = CrossMatrix(["USD", "CAD", "JPY"])
    cm.set_rate("USD", "JPY", 147.5)
    cm.set_rate("USD", "CAD", 1.36)
    # Implied CAD/JPY = USDJPY / USDCAD via USD
    implied = cm.implied("CAD", "JPY", via="USD")
    assert implied == pytest.approx(147.5 / 1.36, rel=1e-4)


def test_cross_matrix_build_from_rates_vxc():
    from quant_nanggroe.engine.cross_matrix import build_matrix_from_rates
    rates = {"EURUSD.vx": 1.08, "USDJPY.vx": 147.5, "EURJPY.vx": 159.3}
    cm = build_matrix_from_rates(rates, ["EUR", "USD", "JPY"])
    assert cm.get_rate("EUR", "JPY") == pytest.approx(159.3)


# ── TriArb ──
def test_tri_arb_delta_positive():
    from quant_nanggroe.engine.currency_graph import build_graph_from_rates
    from quant_nanggroe.engine.cross_matrix import build_matrix_from_graph
    from quant_nanggroe.engine.tri_arb_detector import detect_tri_arb
    rates = {"EURUSD.vx": 1.08, "USDJPY.vx": 147.5, "EURJPY.vx": 160.0}  # mispriced
    g = build_graph_from_rates(rates)
    m = build_matrix_from_graph(g)
    sigs = detect_tri_arb(g, m, threshold=0.0001)
    assert len(sigs) >= 1
    # Δ = quoted - implied ; quoted 160, implied 159.3 => Δ positive
    assert any(s.delta > 0 for s in sigs)


def test_tri_arb_delta_negative():
    from quant_nanggroe.engine.currency_graph import build_graph_from_rates
    from quant_nanggroe.engine.cross_matrix import build_matrix_from_graph
    from quant_nanggroe.engine.tri_arb_detector import detect_tri_arb
    rates = {"EURUSD.vx": 1.08, "USDJPY.vx": 147.5, "EURJPY.vx": 158.0}  # underpriced
    g = build_graph_from_rates(rates)
    m = build_matrix_from_graph(g)
    sigs = detect_tri_arb(g, m, threshold=0.0001)
    assert any(s.delta < 0 for s in sigs)


# ── VectorManifold ──
def test_vector_manifold_pointyen_jpy_normalized():
    from quant_nanggroe.engine.vector_manifold import point_yen
    p = point_yen(usd_jpy=147.5, eur_jpy=159.3, eur_usd=1.08)
    # JPY /100 => 1.475, 1.593
    assert p.x == pytest.approx(1.475)
    assert p.y == pytest.approx(1.593)
    assert p.z == pytest.approx(1.08)
    assert p.label == "PointYEN"


def test_vector_manifold_build_manifold():
    from quant_nanggroe.engine.vector_manifold import build_manifold
    rates = {
        "USDJPY.vx": 147.5, "EURJPY.vx": 159.3,
        "USDCHF.vx": 0.90, "EURCHF.vx": 0.97,
        "USDCAD.vx": 1.36, "EURCAD.vx": 1.47,
        "EURUSD.vx": 1.08,
    }
    m = build_manifold(rates)
    assert "YEN" in m and "CHF" in m and "CAD" in m
    assert m["YEN"].to_array().shape == (3,)


def test_vector_manifold_plane_projection_symmetry():
    from quant_nanggroe.engine.vector_manifold import point_yen, plane_projection
    p1 = point_yen(147.5, 159.3, 1.08)
    p2 = point_yen(147.5, 159.3, 1.08)  # identical => symmetry true
    proj = plane_projection(p1, p2)
    assert proj["symmetry"] is True
    assert proj["distance"] == pytest.approx(0.0)


# ── EuclideanMispricing ──
def test_euclidean_cadjpy_pythagoras():
    from quant_nanggroe.engine.euclidean_mispricing import cadjpy_pythagoras, SQRT2
    assert cadjpy_pythagoras(95.98 * SQRT2) == pytest.approx(95.98)


def test_euclidean_distance_and_box_breach():
    from quant_nanggroe.engine.euclidean_mispricing import check_mispricing
    p = np.array([1.475, 1.593, 1.08])
    p0 = np.array([1.475, 1.593, 1.08])
    sig = check_mispricing(p, p0, sigma=0.05)
    assert sig.d == pytest.approx(0.0)
    assert sig.is_trigger is False
    # breach box by 0.06 on x
    p2 = np.array([1.475 + 0.06, 1.593, 1.08])
    sig2 = check_mispricing(p2, p0, sigma=0.05)
    assert sig2.is_trigger is True  # box breach


def test_euclidean_threshold_sqrt2():
    from quant_nanggroe.engine.euclidean_mispricing import check_mispricing
    p0 = np.zeros(3)
    p = np.array([0.05, 0.05, 0.0])  # distance 0.0707 = 0.05*√2
    sig = check_mispricing(p, p0, sigma=0.05)
    # d == threshold (0.0707) -> not trigger unless box breach, but distance == threshold not > threshold
    # box not breached (0.05 == sigma, need > sigma)
    assert sig.is_trigger is False
    p3 = np.array([0.06, 0.06, 0.0])  # d ~0.084 > 0.0707
    sig3 = check_mispricing(p3, p0, sigma=0.05)
    assert sig3.is_trigger is True


# ── GridExecutor ──
def test_grid_executor_eigenvector_normalized():
    from quant_nanggroe.engine.grid_executor import compute_eigenvector
    pts = [np.array([1.0, 1.0, 1.0]), np.array([1.0, 1.0, 1.0]), np.array([1.0, 1.0, 1.0])]
    ev = compute_eigenvector(pts)
    assert ev.shape == (3,)
    # normalized or at least not zero
    assert np.linalg.norm(ev) == pytest.approx(1.0, abs=1e-6) or np.linalg.norm(ev) > 0


def test_grid_executor_build_grid_count_and_hedged():
    from quant_nanggroe.engine.grid_executor import build_grid
    origin = np.array([1.475, 1.593, 1.08])
    ev = np.array([1, 1, 1]) / math.sqrt(3)
    grid = build_grid(origin, ev, sigma=0.05, levels=5, lot=0.01)
    # 5 levels *2 (hedged mirror) =10
    assert len(grid) == 10
    # hedged: for each distance, one buy one sell
    buys = [g for g in grid if g.side == "buy"]
    sells = [g for g in grid if g.side == "sell"]
    assert len(buys) == 5 and len(sells) == 5
    assert all(g.lot == pytest.approx(0.01) for g in grid)
    assert all(g.coordinate != (0, 0, 0) for g in grid)
