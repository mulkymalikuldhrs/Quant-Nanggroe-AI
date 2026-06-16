import numpy as np

class RecurrencePlotAnalyzer:
    def __init__(self, threshold: float = 0.5, dim: int = 3, delay: int = 1):
        self.threshold = threshold
        self.dim = dim
        self.delay = delay

    def compute_rp(self, series: np.ndarray) -> np.ndarray:
        n = len(series)
        rp = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                rp[i, j] = 1.0 if abs(series[i] - series[j]) < self.threshold else 0.0
        return rp

    def rqa_metrics(self, rp: np.ndarray) -> dict:
        n = rp.shape[0]
        total = n * n
        rr = float(np.sum(rp) / total) if total > 0 else 0
        diag_lengths = []
        for k in range(-n+1, n):
            diag = rp.diagonal(k)
            lengths = np.diff(np.where(np.concatenate(([0], diag, [0])) == 0)[0]) - 1
            diag_lengths.extend(lengths[lengths > 0])
        det = float(sum(l for l in diag_lengths if l >= 2) / max(sum(diag_lengths), 1)) if diag_lengths else 0
        vert_lengths = []
        for j in range(n):
            col = rp[:, j]
            lengths = np.diff(np.where(np.concatenate(([0], col, [0])) == 0)[0]) - 1
            vert_lengths.extend(lengths[lengths > 0])
        laminarity = float(sum(l for l in vert_lengths if l >= 2) / max(sum(vert_lengths), 1)) if vert_lengths else 0
        entropy = float(-np.sum([
            (l / sum(diag_lengths)) * np.log(l / sum(diag_lengths))
            for l in diag_lengths if l > 0
        ])) if diag_lengths else 0
        return {
            "rr": rr,
            "determinism": det,
            "laminarity": laminarity,
            "entropy": entropy,
            "max_line": max(diag_lengths) if diag_lengths else 0,
        }
