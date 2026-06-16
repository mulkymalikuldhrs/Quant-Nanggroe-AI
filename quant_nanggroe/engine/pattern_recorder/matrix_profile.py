import numpy as np

try:
    import stumpy
    HAS_STUMPY = True
except ImportError:
    HAS_STUMPY = False

class MatrixProfileDetector:
    def __init__(self, window: int = 20):
        self.window = window

    def compute_mp(self, series: np.ndarray) -> dict:
        if not HAS_STUMPY:
            return {"error": "stumpy not installed", "motifs": [], "discords": []}
        mp = stumpy.stump(series, self.window)
        motifs = self._find_motifs(mp, series)
        discords = self._find_discords(mp, series)
        return {
            "motifs": motifs,
            "discords": discords,
            "matrix_profile": mp[:, 0].tolist(),
            "matrix_profile_indices": mp[:, 1].tolist(),
        }

    def _find_motifs(self, mp, series, n_motifs: int = 3) -> list[dict]:
        profile = mp[:, 0].copy()
        idx = mp[:, 1].copy()
        motifs = []
        for _ in range(min(n_motifs, len(profile))):
            best_idx = np.argmin(profile)
            if profile[best_idx] == np.inf:
                break
            match_idx = int(idx[best_idx])
            motifs.append({
                "start": int(best_idx),
                "match_start": match_idx,
                "distance": float(profile[best_idx]),
                "window": series[best_idx:best_idx+self.window].tolist(),
            })
            profile[max(0, best_idx-self.window):best_idx+self.window] = np.inf
            profile[max(0, match_idx-self.window):match_idx+self.window] = np.inf
        return motifs

    def _find_discords(self, mp, series, n_discords: int = 3) -> list[dict]:
        profile = mp[:, 0].copy()
        discords = []
        for _ in range(min(n_discords, len(profile))):
            best_idx = np.argmax(profile)
            if profile[best_idx] == -np.inf:
                break
            discords.append({
                "start": int(best_idx),
                "distance": float(profile[best_idx]),
                "window": series[best_idx:best_idx+self.window].tolist(),
            })
            profile[max(0, best_idx-self.window):best_idx+self.window] = -np.inf
        return discords
