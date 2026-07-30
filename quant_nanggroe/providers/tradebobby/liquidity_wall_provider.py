from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class _DepthLevel:
    price: float
    qty: float


@dataclass
class _DepthSnapshot:
    bids: list[_DepthLevel]
    asks: list[_DepthLevel]


class LiquidityWallProvider:
    def __init__(
        self,
        n_snapshots: int = 30,
        wall_threshold: float = 2.2,
        min_frequency: float = 0.6,
    ):
        self._n = n_snapshots
        self._threshold = wall_threshold
        self._min_freq = min_frequency
        self._buffers: dict[str, deque[_DepthSnapshot]] = defaultdict(
            lambda: deque(maxlen=n_snapshots)
        )

    def update_depth(self, symbol: str, bids: list[dict], asks: list[dict]) -> None:
        snap = _DepthSnapshot(
            bids=[_DepthLevel(b["price"], b["qty"]) for b in bids],
            asks=[_DepthLevel(a["price"], a["qty"]) for a in asks],
        )
        self._buffers[symbol].append(snap)

    def get_walls(self, symbol: str) -> dict:
        buf = self._buffers.get(symbol)
        if not buf or len(buf) < 2:
            return {"bid_walls": [], "ask_walls": []}

        N = len(buf)

        level_data: dict[tuple[float, str], dict] = {}
        for snap in buf:
            for level in snap.bids:
                key = (level.price, "bid")
                if key not in level_data:
                    level_data[key] = {"total_qty": 0.0, "count": 0}
                level_data[key]["total_qty"] += level.qty
                level_data[key]["count"] += 1
            for level in snap.asks:
                key = (level.price, "ask")
                if key not in level_data:
                    level_data[key] = {"total_qty": 0.0, "count": 0}
                level_data[key]["total_qty"] += level.qty
                level_data[key]["count"] += 1

        bid_avgs, ask_avgs = [], []
        bid_candidates, ask_candidates = [], []

        for (price, side), data in level_data.items():
            avg_qty = data["total_qty"] / N
            freq = data["count"] / N
            entry = {"price": price, "avg_qty": avg_qty, "frequency": freq}
            if side == "bid":
                bid_avgs.append(avg_qty)
                bid_candidates.append(entry)
            else:
                ask_avgs.append(avg_qty)
                ask_candidates.append(entry)

        bid_global = sum(bid_avgs) / len(bid_avgs) if bid_avgs else 0.0
        ask_global = sum(ask_avgs) / len(ask_avgs) if ask_avgs else 0.0

        def _filter(candidates, global_avg):
            return [
                {
                    "price": e["price"],
                    "qty": round(e["avg_qty"], 2),
                    "frequency": round(e["frequency"], 4),
                    "strength": round(
                        e["avg_qty"] / global_avg if global_avg > 0 else 0.0, 2
                    ),
                }
                for e in candidates
                if e["avg_qty"] > self._threshold * global_avg
                and e["frequency"] >= self._min_freq
            ]

        bid_walls = _filter(bid_candidates, bid_global)
        ask_walls = _filter(ask_candidates, ask_global)
        bid_walls.sort(key=lambda w: w["price"], reverse=True)
        ask_walls.sort(key=lambda w: w["price"])

        return {"bid_walls": bid_walls, "ask_walls": ask_walls}

    def clear_history(self, symbol: str) -> None:
        self._buffers.pop(symbol, None)
