"""
SolSniperX Auto Trader Routes
Flask Blueprint for automated trading configuration and control.
Merged from SolSniperX v3.3.0 (Ultimate Intelligence Upgrade) branch.
"""

import logging
from flask import Blueprint, current_app, request

logger = logging.getLogger(__name__)
auto_trader_bp = Blueprint('auto_trader_bp', __name__, url_prefix='/api/auto-trader')

# Whitelist allowed keys for configuration updates
ALLOWED_CONFIG_KEYS = {
    "min_liquidity", "max_liquidity", "max_age_hours", "min_volume_24h",
    "min_ai_probability_score", "buy_amount_sol", "slippage", "take_profit_tiers",
    "stop_loss_percentage", "trailing_stop_loss_percentage", "max_risk_score",
    "rugcheck_max_score", "use_vwap_filter", "jito_tip_sol", "snipe_only_mode",
    "whitelisted_deployers", "mempool_min_sol_threshold", "mempool_min_liquidity",
    "profit_target_x"
}

@auto_trader_bp.route('/start', methods=['POST'])
async def start_auto_trader():
    """Starts the automated trading bot."""
    auto_trader_service = current_app.services['auto_trader']
    try:
        auto_trader_service.start_trading()
        return {'success': True, 'message': 'Automated trading started.'}
    except Exception as e:
        logger.error(f"Error starting auto trader: {str(e)}")
        return {'success': False, 'error': 'Failed to start automated trading', 'details': str(e)}

@auto_trader_bp.route('/stop', methods=['POST'])
async def stop_auto_trader():
    """Stops the automated trading bot."""
    auto_trader_service = current_app.services['auto_trader']
    try:
        auto_trader_service.stop_trading()
        return {'success': True, 'message': 'Automated trading stopped.'}
    except Exception as e:
        logger.error(f"Error stopping auto trader: {str(e)}")
        return {'success': False, 'error': 'Failed to stop automated trading', 'details': str(e)}

@auto_trader_bp.route('/config', methods=['GET'])
def get_auto_trader_config():
    """Retrieves the current auto trader configuration."""
    auto_trader_service = current_app.services['auto_trader']
    try:
        config = auto_trader_service.get_config()
        return {'success': True, 'data': config}
    except Exception as e:
        logger.error(f"Error fetching auto trader config: {str(e)}")
        return {'success': False, 'error': 'Failed to fetch auto trader configuration', 'details': str(e)}

@auto_trader_bp.route('/config', methods=['POST'])
def update_auto_trader_config():
    """Updates the auto trader configuration."""
    auto_trader_service = current_app.services['auto_trader']
    try:
        data = request.get_json()
        
        if data is None:
            return {'success': False, 'error': 'Invalid JSON or empty request body'}, 400

        new_config = {k: v for k, v in data.items() if k in ALLOWED_CONFIG_KEYS}
        
        if not new_config:
            return {'success': False, 'error': 'No valid configuration parameters provided'}, 400

        auto_trader_service.update_config(new_config)
        return {'success': True, 'message': 'Auto trader configuration updated successfully.'}
    except Exception as e:
        logger.error(f"Error updating auto trader config: {str(e)}")
        return {'success': False, 'error': 'Failed to update auto trader configuration', 'details': str(e)}
