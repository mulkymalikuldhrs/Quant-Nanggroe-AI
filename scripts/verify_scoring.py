"""Verify scoring shims — imports all 8 scorers via engine path and prints OK."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from quant_nanggroe.engine.volatility_scorer import VolatilityScorer
from quant_nanggroe.engine.geo_scorer import GeopoliticalScorer
from quant_nanggroe.engine.positioning_scorer import PositioningScorer
from quant_nanggroe.engine.bond_scorer import BondScorer
from quant_nanggroe.engine.economic_scorer import EconomicScorer
from quant_nanggroe.engine.macro_scorer import MacroScorer
from quant_nanggroe.engine.sentiment_scorer import SentimentScorer
from quant_nanggroe.engine.technical_scorer import TechnicalScorer

# Optional 9th (crypto eliminated per CANONICAL 15.8, but shim exists)
try:
    from quant_nanggroe.engine.crypto_scorer import CryptoScorer  # noqa: F401
    crypto_ok = True
except Exception as e:
    print(f"crypto_scorer import failed: {e}")
    crypto_ok = False

scorers = [
    ("volatility_scorer", VolatilityScorer),
    ("geo_scorer", GeopoliticalScorer),
    ("positioning_scorer", PositioningScorer),
    ("bond_scorer", BondScorer),
    ("economic_scorer", EconomicScorer),
    ("macro_scorer", MacroScorer),
    ("sentiment_scorer", SentimentScorer),
    ("technical_scorer", TechnicalScorer),
]

for name, cls in scorers:
    # instantiate to ensure class is valid
    try:
        obj = cls()
        assert hasattr(obj, "score")
        assert hasattr(obj, "weight")
        print(f"OK {name}: {cls.__name__}")
    except Exception as exc:
        print(f"FAIL {name}: {exc}")
        raise

if crypto_ok:
    print(f"OK crypto_scorer: CryptoScorer")

print("OK - all 8 scorers importable via quant_nanggroe.engine.*_scorer")
