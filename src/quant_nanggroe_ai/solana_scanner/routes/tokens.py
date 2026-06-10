"""
SolSniperX Token Routes
Flask Blueprint for token data retrieval.
Merged from SolSniperX v3.3.0 (Ultimate Intelligence Upgrade) branch.
"""

import logging
from flask import Blueprint, request, current_app

logger = logging.getLogger(__name__)
tokens_bp = Blueprint('tokens_bp', __name__, url_prefix='/api/tokens')

@tokens_bp.route('/', methods=['GET'])
async def get_tokens():
    """Get list of tokens"""
    data_fetcher_service = current_app.services['data_fetcher']
    try:
        tokens = await data_fetcher_service.get_all_tokens()
        return {'success': True, 'data': tokens, 'count': len(tokens)}
    except Exception as e:
        logger.error(f"Error fetching tokens: {str(e)}")
        return {'success': False, 'error': 'Failed to fetch tokens', 'details': str(e)}

@tokens_bp.route('/<token_address>', methods=['GET'])
async def get_token_details(token_address):
    """Get detailed token information"""
    data_fetcher_service = current_app.services['data_fetcher']
    try:
        token = await data_fetcher_service.get_token_by_address(token_address)
        
        if not token:
            return {'success': False, 'error': 'Token not found'}, 404
        
        return {'success': True, 'data': token}
    except Exception as e:
        logger.error(f"Error fetching token details: {str(e)}")
        return {'success': False, 'error': 'Failed to fetch token details', 'details': str(e)}

@tokens_bp.route('/<token_address>/history', methods=['GET'])
async def get_token_history(token_address):
    """Get historical price data for a specific token"""
    data_fetcher_service = current_app.services['data_fetcher']
    try:
        # Validate interval
        interval = request.args.get('interval', '1h')
        if interval not in ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w']:
            interval = '1h'

        # Validate limit
        try:
            limit = int(request.args.get('limit', 24))
            limit = max(1, min(limit, 1000))  # Clamping
        except (ValueError, TypeError):
            limit = 24
        
        history = await data_fetcher_service.get_historical_prices(token_address, interval, limit)
        
        if not history:
            return {'success': False, 'error': 'Historical data not found for token'}, 404
        
        return {'success': True, 'data': history}
    except Exception as e:
        logger.error(f"Error fetching token history: {str(e)}")
        return {'success': False, 'error': 'Failed to fetch token history', 'details': str(e)}
