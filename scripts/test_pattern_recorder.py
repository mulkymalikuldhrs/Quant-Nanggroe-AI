"""Test pattern recorder module"""
import sys; sys.path.insert(0, '..')
import numpy as np
import pandas as pd
from quant_nanggroe.engine.pattern_recorder.dtw import DTWMatcher
from quant_nanggroe.engine.pattern_recorder.embedding import EmbeddingSimilarity

from quant_nanggroe.engine.pattern_recorder.matrix_profile import MatrixProfileDetector

# Test MP with synthetic data
np.random.seed(42)
pattern = np.sin(np.linspace(0, 4*np.pi, 50))
data = np.concatenate([pattern, np.random.randn(100) * 0.1, pattern[:30]])

mp_detector = MatrixProfileDetector(config={"use_stumpy": False})
result = mp_detector.compute(pd.Series(data), window_size=20)
print(f"Matrix Profile: {len(result.motifs)} motifs, {len(result.discords)} discords")
print(f"Mean MP: {result.mean:.4f}, Std MP: {result.std:.4f}")

# Test DTW
dtw = DTWMatcher()
a = np.sin(np.linspace(0, 2*np.pi, 50))
b = np.sin(np.linspace(0.5, 2.5*np.pi, 60))
align = dtw.compute(a, b)
print(f"DTW distance: {align.distance:.4f}, similarity: {align.similarity:.4f}")

# Test Embedding
emb = EmbeddingSimilarity()
q = np.random.randn(40)
db = [np.random.randn(40) for _ in range(10)]
matches = emb.search(q, db, top_k=3)
print(f"Embedding search: {len(matches)} matches")

print("ALL TESTS PASSED")
