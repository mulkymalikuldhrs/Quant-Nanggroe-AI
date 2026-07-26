from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class COTReport:
    asset: str
    report_date: str
    commercial_long: int
    commercial_short: int
    noncommercial_long: int
    noncommercial_short: int
    nonreportable_long: int
    nonreportable_short: int

    @property
    def commercial_net(self) -> int:
        return self.commercial_long - self.commercial_short

    @property
    def noncommercial_net(self) -> int:
        return self.noncommercial_long - self.noncommercial_short

    @property
    def nonreportable_net(self) -> int:
        return self.nonreportable_long - self.nonreportable_short

    @property
    def total_open_interest(self) -> int:
        return (self.commercial_long + self.commercial_short + self.noncommercial_long
                + self.noncommercial_short + self.nonreportable_long + self.nonreportable_short)


COT_CFTC_URLS: dict[str, str] = {
    "GC1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "SI1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "ES1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "NQ1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "6E1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "6B1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "6J1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "6A1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "6C1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "6S1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "ZB1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
    "ZN1!": "https://www.cftc.gov/dea/futures/deacmxsf.htm",
}


class COTProvider:
    def __init__(self):
        self._cache: dict[str, list[COTReport]] = {}
        self._percentile_cache: dict[str, float] = {}

    def parse_csv(self, raw: str, asset: str) -> list[COTReport]:
        reports: list[COTReport] = []
        reader = csv.DictReader(io.StringIO(raw))
        for row in reader:
            try:
                reports.append(COTReport(
                    asset=asset,
                    report_date=row.get("As of Date", row.get("Date", "")),
                    commercial_long=int(row.get("Commercial Long", row.get("Producer Merchant Long", 0))),
                    commercial_short=int(row.get("Commercial Short", row.get("Producer Merchant Short", 0))),
                    noncommercial_long=int(row.get("Noncommercial Long", row.get("Managed Money Long", 0))),
                    noncommercial_short=int(row.get("Noncommercial Short", row.get("Managed Money Short", 0))),
                    nonreportable_long=int(row.get("Nonreportable Long", row.get("Other Reportable Long", 0))),
                    nonreportable_short=int(row.get("Nonreportable Short", row.get("Other Reportable Short", 0))),
                ))
            except (ValueError, TypeError):
                continue
        return reports

    def cache_report(self, asset: str, reports: list[COTReport]) -> None:
        self._cache[asset] = reports
        logger.info("COT cache updated for %s: %d reports", asset, len(reports))

    def evaluate_positioning(self, asset: str, net_positions: float | None = None) -> dict[str, Any]:
        reports = self._cache.get(asset, [])
        if not reports:
            return {
                "asset": asset,
                "status": "NO_DATA",
                "commercial_net": 0,
                "noncommercial_net": 0,
                "nonreportable_net": 0,
                "percentile": 0.5,
                "signal": "neutral",
            }

        latest = reports[-1]
        net_values = [r.noncommercial_net for r in reports]
        hist_min = min(net_values)
        hist_max = max(net_values)
        current_net = net_positions if net_positions is not None else float(latest.noncommercial_net)

        percentile = 0.5
        if hist_max != hist_min:
            percentile = (current_net - hist_min) / (hist_max - hist_min)

        if percentile >= 0.90:
            signal = "extremely_overbought"
        elif percentile >= 0.80:
            signal = "overbought"
        elif percentile <= 0.10:
            signal = "extremely_oversold"
        elif percentile <= 0.20:
            signal = "oversold"
        else:
            signal = "neutral"

        return {
            "asset": asset,
            "report_date": latest.report_date,
            "commercial_net": latest.commercial_net,
            "noncommercial_net": latest.noncommercial_net,
            "nonreportable_net": latest.nonreportable_net,
            "total_open_interest": latest.total_open_interest,
            "percentile": round(percentile, 4),
            "signal": signal,
            "status": "EXTREME_LONG_OVERBOUGHT" if percentile >= 0.90 else "EXTREME_SHORT_OVERSOLD" if percentile <= 0.10 else "BALANCED",
        }

    def get_cached(self, asset: str) -> list[COTReport] | None:
        return self._cache.get(asset)

    def last_updated(self) -> datetime | None:
        if not self._cache:
            return None
        return datetime.now(timezone.utc)
