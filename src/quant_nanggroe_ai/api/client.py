"""
Trading Plan AI Python Client
===============================
Programmatic client for interacting with the Dhaher Trading Plan AI
Google Apps Script backend API.

Merged from Trading-Plan-AI-Interactive branches:
  - main-6589143822304251475 (API key auth, env var support)
  - main-11863369769482398312 (v11.1.4 Production Hardened)
  - mulky-ai-os-v1 (original base)

All import paths use the quant_nanggroe_ai package.

Usage::

    from quant_nanggroe_ai.api.client import TradingPlanClient

    client = TradingPlanClient(
        apps_script_url="https://script.google.com/...",
        api_key="your-bot-api-key",
    )

    # Get AI master summary
    summary = client.get_ai_summary("EURUSD")

    # Get forecast
    forecast = client.get_forecast("GOLD", timeframe="H4", days=7)

    # Log a trade
    client.log_trade({
        "pair": "BTC/USD",
        "direction": "Buy",
        "entry": 60000,
        "sl": 59000,
        "tp": 65000,
        "rrr": 5,
        "setup": "Breakout",
        "mood": "Confident",
    })

    # Log a rule violation
    client.log_violation("TRADE-12345", "No stop loss", "Forgot to set SL")

    # Get journal data
    journal = client.get_journal_data()
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TradingPlanAPIError(Exception):
    """Raised when the Trading Plan API returns an error."""

    def __init__(self, message: str, action: str | None = None, status_code: int | None = None):
        self.action = action
        self.status_code = status_code
        super().__init__(message)


class TradingPlanClient:
    """
    Python client for the Dhaher Trading Plan AI Google Apps Script API.

    This client provides programmatic access to all Trading Plan AI actions:
    - AI master summaries (bias, confidence, thesis, signal)
    - Multi-day forecasts with entry/SL/TP zones
    - Trade journal logging and retrieval
    - Rule violation logging with emotional lockout trigger
    - Weekly analysis triggers
    - Sheet data export

    Args:
        apps_script_url: Google Apps Script web app deployment URL.
        api_key: BOT_API_KEY for authentication. Falls back to
                 ``BOT_API_KEY`` environment variable if not provided.
        timeout: Request timeout in seconds (default: 30).

    Raises:
        ValueError: If ``apps_script_url`` is missing or contains a placeholder.
    """

    VALID_ACTIONS = frozenset({
        "logTrade",
        "getGptFeedback",
        "logViolation",
        "triggerWeeklyAnalysis",
        "exportToJson",
        "getAiMasterSummary",
        "getForecast",
    })

    def __init__(
        self,
        apps_script_url: str,
        api_key: str | None = None,
        timeout: int = 30,
    ) -> None:
        if not apps_script_url or "YOUR_DEPLOYMENT_ID" in apps_script_url:
            raise ValueError(
                "Google Apps Script URL is not configured. "
                "Provide the deployed web app URL or set the GAS_URL env var."
            )
        self.api_url = apps_script_url
        self.api_key = api_key or os.environ.get("BOT_API_KEY")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post_request(self, action: str, data: dict[str, Any] | None = None) -> Any:
        """
        Make a POST request to the GAS backend.

        Args:
            action: The API action name (e.g. ``getAiMasterSummary``).
            data: Optional payload dict.

        Returns:
            The ``data`` field from a successful API response.

        Raises:
            TradingPlanAPIError: On API-level errors or HTTP failures.
        """
        if data is None:
            data = {}

        # Inject API key for authentication
        if self.api_key:
            data["apiKey"] = self.api_key

        payload: dict[str, Any] = {"action": action, "data": data}

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()

            # Google Apps Script can redirect; log the final URL
            if response.history:
                logger.debug("Request redirected. Final URL: %s", response.url)

            result = response.json()

            if result.get("status") == "success":
                return result.get("data")
            else:
                raise TradingPlanAPIError(
                    message=result.get("message", "Unknown API error"),
                    action=action,
                )

        except requests.exceptions.Timeout as exc:
            raise TradingPlanAPIError(
                f"Request timed out after {self.timeout}s", action=action
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise TradingPlanAPIError(
                f"HTTP request failed: {exc}", action=action
            ) from exc
        except json.JSONDecodeError:
            raise TradingPlanAPIError(
                f"Failed to decode JSON response. Raw text: {response.text[:500]}",
                action=action,
            )

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_ai_summary(self, symbol: str = "EURUSD") -> dict[str, Any]:
        """
        Fetch the AI master summary for a given symbol.

        Returns bias, confidence score, technical/fundamental/positional theses,
        and an optional signal (entry, SL, TP).

        Args:
            symbol: Trading pair symbol (e.g. ``EURUSD``, ``GOLD``).

        Returns:
            Dict with keys: final_bias, confidence_score, technical_thesis,
            fundamental_thesis, positional_thesis, signal, cot_raw.
        """
        logger.info("Fetching AI summary for %s", symbol)
        return self._post_request("getAiMasterSummary", {"symbol": symbol})

    def get_forecast(
        self,
        symbol: str = "EURUSD",
        timeframe: str = "H4",
        days: int = 7,
    ) -> dict[str, Any]:
        """
        Fetch a multi-day AI forecast for a given symbol.

        Args:
            symbol: Trading pair symbol.
            timeframe: Chart timeframe (e.g. ``H4``, ``D1``).
            days: Number of days to forecast.

        Returns:
            Dict with keys: bias, entry_zone, confirmation, stop_loss,
            take_profit, probability, is_tradeable.
        """
        logger.info("Fetching forecast for %s (%s, %d days)", symbol, timeframe, days)
        return self._post_request(
            "getForecast",
            {"pair": symbol, "timeframe": timeframe, "days": days},
        )

    def get_journal_data(self, sheet_name: str = "Journal") -> list[dict[str, Any]]:
        """
        Export the trading journal as a list of dictionaries.

        Args:
            sheet_name: Google Sheet tab name (default: ``Journal``).

        Returns:
            List of dicts, one per journal row.
        """
        logger.info("Fetching journal data from sheet '%s'", sheet_name)
        raw = self._post_request("exportToJson", {"sheetName": sheet_name})
        # GAS sometimes returns JSON as a string; parse it
        if isinstance(raw, str):
            return json.loads(raw)
        return raw

    def log_trade(self, trade_data: dict[str, Any]) -> str:
        """
        Log a new trade to the journal.

        Args:
            trade_data: Dict with trade fields. Expected keys:
                pair, direction, entry, sl, tp, rrr, setup, mood,
                ai_status, result, emotion_after, gpt_comment, pnl.

        Returns:
            Confirmation string from the API.
        """
        pair = trade_data.get("pair", "UNKNOWN")
        logger.info("Logging trade for %s", pair)
        return self._post_request("logTrade", trade_data)

    def log_violation(
        self,
        trade_id: str,
        rule: str,
        justification: str,
    ) -> str:
        """
        Log a rule violation. Triggers emotional lockout after 3 consecutive violations.

        Args:
            trade_id: The trade identifier (e.g. ``TRADE-12345``).
            rule: The rule that was broken.
            justification: Why the rule was broken.

        Returns:
            Confirmation string from the API.
        """
        logger.info("Logging violation for trade %s: %s", trade_id, rule)
        return self._post_request(
            "logViolation",
            {"tradeId": trade_id, "ruleBroken": rule, "justification": justification},
        )

    def trigger_weekly_analysis(self) -> Any:
        """
        Trigger the automated weekly analysis and summary.

        Returns:
            Weekly analysis result from the API.
        """
        logger.info("Triggering weekly analysis")
        return self._post_request("triggerWeeklyAnalysis", {})

    def get_gpt_feedback(
        self,
        prompt_type: str,
        prompt_data: dict[str, Any] | None = None,
        full_prompt: str | None = None,
        reference_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get GPT/LLM feedback on a specific prompt type.

        Args:
            prompt_type: Type of prompt (e.g. ``EntryValidation``, ``WeeklySummary``).
            prompt_data: Template variables for the prompt.
            full_prompt: Override the template with a full prompt string.
            reference_id: Optional reference ID for tracking.

        Returns:
            Parsed JSON response from GPT.
        """
        data: dict[str, Any] = {"promptType": prompt_type}
        if prompt_data:
            data["promptData"] = prompt_data
        if full_prompt:
            data["full_prompt"] = full_prompt
        if reference_id:
            data["referenceId"] = reference_id

        logger.info("Getting GPT feedback: prompt_type=%s", prompt_type)
        return self._post_request("getGptFeedback", data)

    def export_sheet(self, sheet_name: str) -> list[dict[str, Any]] | str:
        """
        Export any Google Sheet tab to a list of dicts.

        Args:
            sheet_name: The tab name to export.

        Returns:
            List of row dicts, or raw string if parsing fails.
        """
        logger.info("Exporting sheet: %s", sheet_name)
        return self._post_request("exportToJson", {"sheetName": sheet_name})

    # ------------------------------------------------------------------
    # Convenience: raw action call
    # ------------------------------------------------------------------

    def call(self, action: str, data: dict[str, Any] | None = None) -> Any:
        """
        Make a raw API call with any valid action.

        Args:
            action: One of the valid GAS actions.
            data: Payload dict.

        Returns:
            API response data.

        Raises:
            ValueError: If the action is not recognized.
        """
        if action not in self.VALID_ACTIONS:
            raise ValueError(
                f"Invalid action '{action}'. Valid: {sorted(self.VALID_ACTIONS)}"
            )
        return self._post_request(action, data)


# ══════════════════════════════════════════════════════════════════════
# Convenience factory
# ══════════════════════════════════════════════════════════════════════

def create_client_from_env() -> TradingPlanClient:
    """
    Create a :class:`TradingPlanClient` from environment variables.

    Required env vars:
        GAS_URL: Google Apps Script deployment URL.
        BOT_API_KEY: API key for authentication.

    Returns:
        Configured TradingPlanClient instance.

    Raises:
        ValueError: If GAS_URL is not set.
    """
    url = os.environ.get("GAS_URL", "")
    api_key = os.environ.get("BOT_API_KEY", "")
    return TradingPlanClient(apps_script_url=url, api_key=api_key)


# ══════════════════════════════════════════════════════════════════════
# Quick demo (run as script)
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    url = os.environ.get("GAS_URL", "")
    key = os.environ.get("BOT_API_KEY", "")

    if not url:
        print("Set GAS_URL and BOT_API_KEY env vars to test the client.")
    else:
        try:
            client = TradingPlanClient(url, key)
            journal = client.get_journal_data()
            print(f"Fetched {len(journal)} journal entries.")
        except (TradingPlanAPIError, ValueError) as exc:
            print(f"Error: {exc}")
