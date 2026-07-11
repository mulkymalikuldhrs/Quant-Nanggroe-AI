from dataclasses import dataclass, field

import numpy as np


@dataclass
class PatternEntry:
    pattern_id: str
    timestamp: str
    window: list[float]
    features: dict
    performance: dict
    similarity_cache: dict = field(default_factory=dict)

class PatternRegistry:
    def __init__(self):
        self.patterns: dict[str, PatternEntry] = {}
        self.by_similarity: dict[str, list[str]] = {}

    def register(self, pattern: PatternEntry):
        self.patterns[pattern.pattern_id] = pattern

    def search(self, query_window: np.ndarray, threshold: float = 0.8) -> list[PatternEntry]:
        matches = []
        for pid, pat in self.patterns.items():
            sim = float(
                np.dot(query_window, pat.window[:len(query_window)]) /
                (np.linalg.norm(query_window) * np.linalg.norm(pat.window[:len(query_window)]) + 1e-8)
            )
            if sim >= threshold:
                matches.append(pat)
        return sorted(matches, key=lambda x: x.performance.get("sharpe", 0), reverse=True)[:10]

    def stats(self) -> dict:
        avg_perf = np.mean([p.performance.get("return", 0) for p in self.patterns.values()]) if self.patterns else 0
        return {"total_patterns": len(self.patterns), "avg_performance": avg_perf}
