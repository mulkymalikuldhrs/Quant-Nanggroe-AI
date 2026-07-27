"""Risk Guard — Veto Power untuk Hedge Fund (adaptasi dari AI Market Maker)

Sebelum trade dieksekusi ke MT5, Risk Guard akan:
1. Hitung risk score dari portfolio + market context
2. VETOED jika risk > threshold (default 0.8)
3. Kill switch via env var HEDGE_KILL_SWITCH
4. Catat reasoning ke file log

Integrasi: panggil risk_guard.approve(proposal) sebelum hedge_fund_mtf.py execute.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger('risk_guard')
LOG_DIR = Path(__file__).parent / 'data' / 'risk_guard'
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _env_truthy(name: str) -> bool:
    v = (os.getenv(name) or '').strip().lower()
    return v in ('1', 'true', 'yes', 'on')


def _load_policy(policy_path: Optional[Path] = None) -> dict:
    """Load risk policy dari file JSON atau default."""
    default = {
        "risk_max_drawdown_stop": 0.20,
        "max_leverage": 3.0,
        "max_daily_loss": 0.05,
        "max_weekly_loss": 0.03,
        "max_position_size": 0.02,
        "risk_score_threshold": 0.8,
        "concentration_limit": 0.3,
    }
    if policy_path and policy_path.exists():
        try:
            with open(policy_path) as f:
                return {**default, **json.load(f)}
        except Exception:
            log.warning(f"Failed to load policy {policy_path}, using default")
    return default


def calculate_risk_score(proposal: Dict[str, Any], policy: dict) -> tuple[float, list[str]]:
    """Calculate risk score 0.0 (safe) to 1.0 (veto).
    
    proposal keys:
    - symbol: str
    - action: 'buy' | 'sell'
    - volume: float
    - price: float
    - sl: float (stop loss)
    - account_balance: float
    - daily_pnl: float
    - open_positions: int
    - market_volatility: float (ATR / price)
    """
    risk = 0.0
    reasons = []
    
    # 1. Position size vs balance — fail-closed: missing balance -> veto
    balance = proposal.get('account_balance')
    if balance is None or balance <= 0:
        risk = max(risk, 1.0)
        reasons.append("missing_or_invalid_account_balance")
        return min(1.0, max(0.0, risk)), reasons[:6]
    volume = proposal.get('volume', 0.01)
    notional = volume * proposal.get('price', 1.0)
    pos_ratio = notional / balance if balance > 0 else 1.0
    max_pos = policy.get('max_position_size', 0.02)

    if pos_ratio > max_pos * 1.5:
        risk = max(risk, 0.95)
        reasons.append(f"position_too_large ratio={pos_ratio:.2%} > {max_pos:.2%}")
    elif pos_ratio > max_pos:
        risk = max(risk, 0.75)
        reasons.append(f"position_large ratio={pos_ratio:.2%} ~ {max_pos:.2%}")

    # 2. Daily loss limit — fail-closed: missing/unknown daily_pnl -> veto
    daily_pnl = proposal.get('daily_pnl')
    max_loss = policy.get('max_daily_loss', 0.05)
    if daily_pnl is None:
        # Cannot assess the loss limit on unknown P&L -> fail-closed veto
        # (phantom-veto defense: never auto-approve when realized P&L is absent).
        risk = max(risk, 1.0)
        reasons.append("missing_daily_pnl_unknown_risk")
        return min(1.0, max(0.0, risk)), reasons[:6]
    loss_ratio = abs(daily_pnl) / balance if daily_pnl < 0 else 0
    
    if loss_ratio > max_loss * 1.2:
        risk = max(risk, 1.0)
        reasons.append(f"daily_loss_limit_hit loss={loss_ratio:.2%} > {max_loss:.2%}")
    elif loss_ratio > max_loss:
        risk = max(risk, 0.85)
        reasons.append(f"daily_loss_high loss={loss_ratio:.2%} ~ {max_loss:.2%}")
    
    # 2b. Weekly loss limit — caution on missing data.
    # Unlike daily_pnl (must-have every session), weekly_pnl can be missing
    # during broker reconnections or week boundaries. Missing weekly data
    # bumps baseline risk but does NOT veto — a stale 0.0 is safer than a hard halt.
    weekly_pnl = proposal.get('weekly_pnl')
    max_weekly_loss = policy.get('max_weekly_loss', 0.03)
    if weekly_pnl is None:
        # No weekly data available — cannot assess weekly loss.
        # Bump risk conservatively but allow the trade (degraded mode).
        risk = max(risk, 0.5)
        # Do NOT append to reasons — this keeps the no-evidence veto intact.
        # If no other real risk reason fires and no signal/confidence exists,
        # the guard still vetoes via the no-evidence path below.
        weekly_pnl = 0.0  # treat as zero for loss calc
    week_loss_ratio = abs(weekly_pnl) / balance if weekly_pnl < 0 else 0
    if week_loss_ratio > max_weekly_loss * 1.2:
        risk = max(risk, 1.0)
        reasons.append(f"weekly_loss_limit_hit loss={week_loss_ratio:.2%} > {max_weekly_loss:.2%}")
    elif week_loss_ratio > max_weekly_loss:
        risk = max(risk, 0.85)
        reasons.append(f"weekly_loss_high loss={week_loss_ratio:.2%} ~ {max_weekly_loss:.2%}")
    
    # 3. Concentration (open positions)
    open_pos = proposal.get('open_positions', 0)
    max_positions = 5  # hard limit
    if open_pos >= max_positions:
        risk = max(risk, 0.9)
        reasons.append(f"max_positions_reached {open_pos} >= {max_positions}")
    elif open_pos >= max_positions - 1:
        risk = max(risk, 0.6)
        reasons.append(f"near_max_positions {open_pos}/{max_positions}")
    
    # 4. Market volatility
    vol = proposal.get('market_volatility', 0.0)
    if vol > 0.05:  # 5% intraday vol
        risk = max(risk, min(1.0, vol * 5))
        reasons.append(f"high_volatility vol={vol:.4f}")
    
    # 5. Stop loss distance
    price = proposal.get('price', 0)
    sl = proposal.get('sl', 0)
    if price > 0 and sl > 0:
        sl_pct = abs(price - sl) / price
        if sl_pct > 0.05:  # SL > 5% = risky
            risk = max(risk, min(0.9, sl_pct * 10))
            reasons.append(f"wide_stop_loss sl={sl_pct:.2%}")
    
    # Default: fail-closed veto when no risk reasons fire.
    # A trading signal is not a safety justification — it is a conviction claim,
    # not a risk checkpoint. Approving on conviction alone = rubber stamp.
    if not reasons:
        risk = 1.0
        reasons.append("no_risk_evidence_veto")
    
    return min(1.0, max(0.0, risk)), reasons[:6]


def approve(proposal: Dict[str, Any], 
            policy_path: Optional[Path] = None,
            log_veto: bool = True) -> Dict[str, Any]:
    """Main entry: check proposal and return APPROVED/VETOED.
    
    Returns:
    - status: 'APPROVED' | 'VETOED'
    - risk_score: float 0-1
    - reasons: list[str]
    - timestamp: str
    """
    # Kill switch
    if _env_truthy('HEDGE_KILL_SWITCH') or _env_truthy('HEDGE_RISK_GUARD_KILL'):
        return {
            'status': 'VETOED',
            'risk_score': 1.0,
            'reasons': ['kill_switch_active'],
            'timestamp': datetime.now().isoformat(),
        }
    
    policy = _load_policy(policy_path)
    threshold = policy.get('risk_score_threshold', 0.8)
    
    risk_score, reasons = calculate_risk_score(proposal, policy)
    is_vetoed = risk_score > threshold
    
    result = {
        'status': 'VETOED' if is_vetoed else 'APPROVED',
        'risk_score': risk_score,
        'reasons': reasons,
        'threshold': threshold,
        'timestamp': datetime.now().isoformat(),
    }
    
    if log_veto:
        _log_decision(result, proposal)
    
    return result


def _log_decision(decision: dict, proposal: dict):
    """Log keputusan Risk Guard ke file."""
    log_entry = {
        'decision': decision,
        'proposal_summary': {
            'symbol': proposal.get('symbol'),
            'action': proposal.get('action'),
            'volume': proposal.get('volume'),
            'price': proposal.get('price'),
        }
    }
    log_file = LOG_DIR / f"decisions_{datetime.now().strftime('%Y%m%d')}.jsonl"
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        log.warning(f"Failed to log decision: {e}")


# Quick test
if __name__ == '__main__':
    # Contoh proposal buy
    test_proposal = {
        'symbol': 'EURUSD',
        'action': 'buy',
        'volume': 0.02,
        'price': 1.14415,
        'sl': 1.14315,
        'account_balance': 1000.0,
        'daily_pnl': -15.0,
        'open_positions': 1,
        'market_volatility': 0.001,
    }
    result = approve(test_proposal)
    print(json.dumps(result, indent=2))
