import numpy as np

class DTWPatternMatcher:
    def __init__(self, sakoe_chiba_band: int = 5):
        self.band = sakoe_chiba_band

    def dtw_distance(self, a: np.ndarray, b: np.ndarray) -> float:
        n, m = len(a), len(b)
        dtw = np.full((n+1, m+1), np.inf)
        dtw[0, 0] = 0
        for i in range(1, n+1):
            for j in range(max(1, i-self.band), min(m+1, i+self.band+1)):
                cost = abs(a[i-1] - b[j-1])
                dtw[i, j] = cost + min(dtw[i-1, j], dtw[i, j-1], dtw[i-1, j-1])
        return float(dtw[n, m])

    def lb_keogh(self, a: np.ndarray, b: np.ndarray) -> float:
        n = min(len(a), len(b))
        lower, upper = np.full(n, np.inf), np.full(n, -np.inf)
        for i in range(n):
            lo = max(0, i-self.band)
            hi = min(n-1, i+self.band)
            lower[i] = np.min(b[lo:hi+1]) if lo <= hi else b[i]
            upper[i] = np.max(b[lo:hi+1]) if lo <= hi else b[i]
        return float(np.sum(
            (a[:n] - upper)**2 * (a[:n] > upper) +
            (lower - a[:n])**2 * (a[:n] < lower)
        ))

    def match(self, query: np.ndarray, database: list[np.ndarray], k: int = 5) -> list[dict]:
        results = []
        for i, pattern in enumerate(database):
            lb = self.lb_keogh(query, pattern)
            if lb > np.inf:
                continue
            d = self.dtw_distance(query, pattern)
            results.append({"index": i, "distance": d, "similarity": 1.0 / (1.0 + d)})
        results.sort(key=lambda x: x["distance"])
        return results[:k]
