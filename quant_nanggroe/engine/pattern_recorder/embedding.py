import numpy as np

class EmbeddingSimilarity:
    def __init__(self, dim: int = 64):
        self.dim = dim
        self.index: list[tuple[np.ndarray, dict]] = []

    def encode(self, window: np.ndarray, n_bins: int = 10) -> np.ndarray:
        vec = np.zeros(self.dim)
        normalized = (window - window.mean()) / max(window.std(), 1e-8)
        for i in range(min(len(normalized), self.dim)):
            vec[i] = normalized[i]
        return vec

    def build_index(self, patterns: list[tuple[np.ndarray, dict]]):
        self.index = [(self.encode(p), meta) for p, meta in patterns]

    def search(self, query: np.ndarray, k: int = 5) -> list[dict]:
        q_vec = self.encode(query)
        results = []
        for vec, meta in self.index:
            sim = float(np.dot(q_vec, vec) / (np.linalg.norm(q_vec) * np.linalg.norm(vec) + 1e-8))
            results.append({"similarity": sim, "metadata": meta})
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]
