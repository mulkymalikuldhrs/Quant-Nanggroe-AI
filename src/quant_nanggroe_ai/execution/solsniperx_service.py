"""
SolSniperX Backend Service Entry Point
Flask-SocketIO application with async background services.
Merged from SolSniperX v3.3.0 (Ultimate Intelligence Upgrade) branch.

This module provides the SolSniperX backend server that integrates:
- Token scanning and data fetching
- AI-powered token analysis
- Mempool monitoring for new tokens and rugpull detection
- Automated and manual trading via Jupiter Aggregator
- Wallet management on Solana
- Limit order execution
- Service watchdog for autonomous resilience
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import logging
import asyncio
import threading
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

from quant_nanggroe_ai.solana_scanner.data_fetcher import data_fetcher_service
from quant_nanggroe_ai.solana_scanner.mempool_monitor import mempool_monitor_service
from quant_nanggroe_ai.solana_scanner.trading_service import trading_service
from quant_nanggroe_ai.solana_scanner.wallet_service import wallet_service
from quant_nanggroe_ai.solana_scanner.ai_analysis import ai_analysis_service
from quant_nanggroe_ai.solana_scanner.auto_trader import auto_trader_service

# Import Blueprints
from quant_nanggroe_ai.solana_scanner.routes.tokens import tokens_bp
from quant_nanggroe_ai.solana_scanner.routes.auto_trader import auto_trader_bp

from quant_nanggroe_ai.solana_scanner.db import init_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask-SocketIO application."""
    app = Flask(__name__)
    CORS(app, origins=os.getenv('CORS_ORIGIN', 'http://localhost:5173'))
    socketio = SocketIO(app, cors_allowed_origins=os.getenv('CORS_ORIGIN', 'http://localhost:5173'), async_mode='threading')

    # Service definitions
    app.services = {}

    # Register Blueprints
    app.register_blueprint(tokens_bp)
    app.register_blueprint(auto_trader_bp)

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'SolSniperX Backend v3.3.0 (Ultimate Intelligence Upgrade)',
            'features': [
                'Token Scanner', 'AI Analysis', 'Trading Signals', 'Local Storage',
                'RugCheck API', 'JITO Support', 'Dynamic JITO Tip',
                'Consolidated Production Ready', 'Advanced Mempool Filtering',
                'Service Watchdog', 'Autonomous Resilience',
                'Social Metadata Extraction', 'Enhanced AI Intelligence'
            ]
        })

    @app.errorhandler(404)
    def not_found(error):
        return {'success': False, 'error': 'Endpoint not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return {'success': False, 'error': 'Internal server error'}, 500

    return app, socketio


def start_async_loop(socketio):
    """
    Starts an asyncio event loop in a background thread for monitoring and auto-trading.
    """
    background_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(background_loop)

    # Inform services about the background loop
    auto_trader_service.set_loop(background_loop)

    # Run post_init in the background loop
    background_loop.create_task(auto_trader_service.post_init())

    # Schedule background tasks - access properties to initialize them within the loop context
    _ = data_fetcher_service.http_client
    _ = ai_analysis_service.http_client
    _ = trading_service.solana_client
    _ = trading_service.http_client
    _ = wallet_service.solana_client
    _ = wallet_service.http_client

    background_loop.create_task(mempool_monitor_service.start_monitoring())

    # Start limit order checker
    async def limit_order_loop():
        while True:
            try:
                await trading_service.check_and_execute_limit_orders()
            except Exception as e:
                logger.error(f"Error in limit order loop: {e}")
            await asyncio.sleep(30)  # Check every 30 seconds

    background_loop.create_task(limit_order_loop())

    # Start service watchdog
    async def monitor_services_loop():
        logger.info("Service watchdog started.")
        while True:
            try:
                # Check Mempool Monitor
                if mempool_monitor_service.is_running:
                    if mempool_monitor_service.monitoring_task is None or mempool_monitor_service.monitoring_task.done():
                        logger.warning("Mempool monitor task is not running but is_running is True. Restarting...")
                        await mempool_monitor_service.start_monitoring()

                # Check Auto Trader
                if auto_trader_service.trading_enabled:
                    if auto_trader_service.trade_loop_task is None or auto_trader_service.trade_loop_task.done():
                        logger.warning("Auto trader trade loop is not running but trading_enabled is True. Restarting...")
                        auto_trader_service.start_trading()

            except Exception as e:
                logger.error(f"Error in service watchdog: {e}")
            await asyncio.sleep(60)  # Check every 60 seconds

    background_loop.create_task(monitor_services_loop())

    logger.info("Background asyncio loop started.")
    background_loop.run_forever()


def run_server():
    """Main entry point to run the SolSniperX backend server."""
    app, socketio = create_app()

    # Initialize database
    init_db()

    # Service Initialization with socketio
    wallet_service.socketio = socketio
    wallet_service.data_fetcher_service = data_fetcher_service

    trading_service.socketio = socketio
    trading_service.data_fetcher_service = data_fetcher_service

    mempool_monitor_service.socketio = socketio
    mempool_monitor_service.data_fetcher_service = data_fetcher_service

    data_fetcher_service.socketio = socketio

    ai_analysis_service.socketio = socketio
    ai_analysis_service.data_fetcher_service = data_fetcher_service

    auto_trader_service.socketio = socketio
    auto_trader_service.data_fetcher_service = data_fetcher_service
    auto_trader_service.ai_analysis_service = ai_analysis_service
    auto_trader_service.trading_service = trading_service
    auto_trader_service.wallet_service = wallet_service

    # Setup callbacks for autonomous action
    mempool_monitor_service.on_new_token(auto_trader_service.handle_new_token)
    mempool_monitor_service.on_rugpull(auto_trader_service.handle_rugpull_alert)

    # Update app.services
    app.services.update({
        "wallet": wallet_service,
        "trading": trading_service,
        "mempool": mempool_monitor_service,
        "data_fetcher": data_fetcher_service,
        "ai_analysis": ai_analysis_service,
        "auto_trader": auto_trader_service
    })

    # Start background asyncio services in a dedicated thread
    bg_thread = threading.Thread(target=start_async_loop, args=(socketio,), daemon=True)
    bg_thread.start()

    # Run the Flask-SocketIO app
    logger.info("Starting Flask-SocketIO server on port 5000...")
    socketio.run(app, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    run_server()
