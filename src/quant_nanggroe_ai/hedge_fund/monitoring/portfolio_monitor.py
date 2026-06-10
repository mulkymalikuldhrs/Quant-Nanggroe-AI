"""
Real-time Portfolio Monitor for AI Quant Hedge Fund
Provides portfolio tracking, PnL calculation, and WebSocket broadcasting
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set, Any
from dataclasses import dataclass

from src.monitoring.portfolio_models import (
    Portfolio,
    Position,
    Trade,
    OrderSide
)

logger = logging.getLogger(__name__)


@dataclass
class MonitorConfig:
    """Configuration for portfolio monitor."""
    update_interval: float = 1.0
    reconnect_delay: float = 5.0
    max_reconnect_attempts: int = 5
    enable_websocket: bool = True
    websocket_port: int = 8765
    enable_price_cache: bool = True
    price_cache_ttl: float = 0.5
    log_level: str = "INFO"


class PortfolioMonitor:
    """
    Real-time portfolio monitoring with PnL tracking.
    
    Features:
    - Continuous portfolio updates from broker
    - PnL calculation
    - WebSocket broadcasting for real-time updates
    - Price caching for performance
    - Subscription system for callbacks
    """
    
    def __init__(
        self,
        broker=None,
        config: MonitorConfig = None
    ):
        self.broker = broker
        self.config = config or MonitorConfig()
        self.portfolio = Portfolio()
        self.running = False
        self._update_task = None
        self._subscribers: Set[Callable] = set()
        self._price_cache: Dict[str, Dict] = {}
        self._price_cache_times: Dict[str, datetime] = {}
        self._websocket_server = None
        self._reconnect_attempts = 0
        
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def subscribe(self, callback: Callable) -> None:
        """
        Subscribe to portfolio updates.
        
        Args:
            callback: Function to call on updates, receives (portfolio, update_type)
        """
        self._subscribers.add(callback)
        logger.info(f"Subscriber added. Total subscribers: {len(self._subscribers)}")
    
    def unsubscribe(self, callback: Callable) -> None:
        """Remove a subscriber."""
        self._subscribers.discard(callback)
        logger.info(f"Subscriber removed. Total subscribers: {len(self._subscribers)}")
    
    def _notify_subscribers(
        self,
        update_type: str,
        data: Dict = None
    ) -> None:
        """Notify all subscribers of update."""
        for callback in self._subscribers:
            try:
                callback(self.portfolio, update_type, data)
            except Exception as e:
                logger.error(f"Subscriber callback failed: {e}")
    
    async def start(self) -> None:
        """Start the portfolio monitor."""
        if self.running:
            logger.warning("Monitor already running")
            return
        
        self.running = True
        logger.info("Starting portfolio monitor")
        
        if self.config.enable_websocket:
            await self._start_websocket_server()
        
        self._update_task = asyncio.create_task(self._update_loop())
        logger.info("Portfolio monitor started")
    
    async def stop(self) -> None:
        """Stop the portfolio monitor."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping portfolio monitor")
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        if self._websocket_server:
            await self._stop_websocket_server()
        
        logger.info("Portfolio monitor stopped")
    
    async def _update_loop(self) -> None:
        """Main update loop."""
        while self.running:
            try:
                await self._update_portfolio()
                await self._notify_subscribers("update", {"timestamp": datetime.now().isoformat()})
                
                if self._websocket_server:
                    await self._websocket_server.broadcast_portfolio(self.portfolio)
                
                await asyncio.sleep(self.config.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Update loop error: {e}")
                await asyncio.sleep(self.config.reconnect_delay)
    
    async def _update_portfolio(self) -> None:
        """Update portfolio from broker."""
        if self.broker is None:
            return
        
        try:
            account = self.broker.get_account_info()
            positions = self.broker.get_positions()
            
            if account:
                self._update_account(account)
            
            if positions:
                self._update_positions(positions)
            
            self._reconnect_attempts = 0
            
        except Exception as e:
            self._reconnect_attempts += 1
            logger.error(f"Error updating portfolio: {e}")
            
            if self._reconnect_attempts >= self.config.max_reconnect_attempts:
                logger.error("Max reconnect attempts reached")
                await self._handle_connection_loss()
    
    def _update_account(self, account_info: Dict) -> None:
        """Update account information."""
        self.portfolio.account_balance = account_info.get("balance", self.portfolio.account_balance)
        self.portfolio.account_equity = account_info.get("equity", self.portfolio.account_equity)
        self.portfolio.margin_used = account_info.get("margin", 0)
        self.portfolio.margin_free = account_info.get("margin_free", 0)
        self.portfolio.margin_level = account_info.get("margin_level", 0)
        self.portfolio.last_equity_update = datetime.now()
    
    def _update_positions(self, positions: List[Dict]) -> None:
        """Update position prices and PnL."""
        for pos_data in positions:
            ticket = pos_data["ticket"]
            
            if ticket in self.portfolio.positions:
                position = self.portfolio.positions[ticket]
                
                current_price = pos_data.get("current_price")
                pnl = pos_data.get("pnl", 0)
                
                if current_price:
                    position.current_price = current_price
                    position.pnl = pnl
                
                self._update_price_cache(position.symbol, current_price)
    
    def _update_price_cache(self, symbol: str, price: float) -> None:
        """Update price cache for a symbol."""
        if price is None:
            return
        
        now = datetime.now()
        self._price_cache[symbol] = {
            "bid": price * 0.9999,
            "ask": price * 1.0001,
            "last": price
        }
        self._price_cache_times[symbol] = now
    
    def get_cached_price(self, symbol: str) -> Optional[Dict]:
        """
        Get cached price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict with bid, ask, last or None
        """
        if not self.config.enable_price_cache:
            return None
        
        now = datetime.now()
        
        if symbol in self._price_cache:
            cache_time = self._price_cache_times.get(symbol)
            if cache_time and (now - cache_time).total_seconds() < self.config.price_cache_ttl:
                return self._price_cache[symbol]
        
        return None
    
    def get_portfolio_snapshot(self) -> Dict:
        """Get current portfolio snapshot."""
        stats = self.portfolio.calculate_statistics()
        
        return {
            "timestamp": self.portfolio.last_update.isoformat(),
            "account": {
                "id": self.portfolio.account_id,
                "balance": self.portfolio.account_balance,
                "equity": self.portfolio.account_equity,
                "currency": self.portfolio.account_currency,
                "margin_used": self.portfolio.margin_used,
                "margin_free": self.portfolio.margin_free,
                "margin_level": self.portfolio.margin_level
            },
            "positions": {
                str(ticket): pos.to_dict()
                for ticket, pos in self.portfolio.positions.items()
            },
            "position_count": self.portfolio.open_positions_count,
            "trade_count": self.portfolio.closed_trades_count,
            "statistics": stats,
            "exposure": {
                "long": self.portfolio.long_exposure,
                "short": self.portfolio.short_exposure,
                "net": self.portfolio.net_exposure,
                "gross": self.portfolio.gross_exposure,
                "ratio": self.portfolio.exposure_ratio
            },
            "performance": {
                "daily_pnl": self.portfolio.daily_pnl,
                "total_pnl": self.portfolio.total_pnl,
                "win_rate": self.portfolio.win_rate,
                "profit_factor": self.portfolio.profit_factor,
                "expectancy": self.portfolio.expectancy
            }
        }
    
    async def add_position_from_broker(self, position_data: Dict) -> None:
        """
        Add a position from broker data.
        
        Args:
            position_data: Position data from broker
        """
        ticket = position_data["ticket"]
        
        if ticket in self.portfolio.positions:
            logger.warning(f"Position {ticket} already exists")
            return
        
        side = OrderSide.BUY if position_data.get("type") == "BUY" else OrderSide.SELL
        
        position = Position(
            ticket=ticket,
            symbol=position_data["symbol"],
            side=side,
            volume=position_data["volume"],
            open_price=position_data["open_price"],
            open_time=position_data.get("time", datetime.now()),
            sl=position_data.get("sl"),
            tp=position_data.get("tp"),
            current_price=position_data.get("current_price"),
            commission=position_data.get("commission", 0),
            swap=position_data.get("swap", 0),
            magic=position_data.get("magic", 9001),
            comment=position_data.get("comment", "")
        )
        
        self.portfolio.add_position(position)
        self._notify_subscribers("position_opened", {"position": position.to_dict()})
        logger.info(f"Position added: {position.symbol} {position.side.value} {position.volume}")
    
    async def close_position_from_broker(
        self,
        ticket: int,
        close_data: Dict = None
    ) -> None:
        """
        Close a position from broker data.
        
        Args:
            ticket: Position ticket
            close_data: Close result data
        """
        position = self.portfolio.remove_position(ticket)
        
        if position is None:
            logger.warning(f"Position {ticket} not found")
            return
        
        if close_data:
            exit_price = close_data.get("price", position.current_price or position.open_price)
            exit_time = datetime.now()
            
            trade = Trade.from_position(
                position,
                exit_price,
                exit_time,
                exit_reason=close_data.get("comment", "Broker close")
            )
            
            self.portfolio.add_trade(trade)
            self._notify_subscribers("trade_closed", {"trade": trade.to_dict()})
            logger.info(f"Trade closed: {trade.symbol} {trade.side.value} PnL: {trade.pnl:.2f}")
        else:
            self._notify_subscribers("position_closed", {"ticket": ticket})
            logger.info(f"Position closed: {ticket}")
    
    async def _handle_connection_loss(self) -> None:
        """Handle connection loss to broker."""
        logger.error("Connection to broker lost")
        self._notify_subscribers("connection_lost", {})
    
    async def _start_websocket_server(self) -> None:
        """Start WebSocket server for real-time updates."""
        try:
            self._websocket_server = PortfolioWebSocketServer(
                port=self.config.websocket_port,
                monitor=self
            )
            await self._websocket_server.start()
            logger.info(f"WebSocket server started on port {self.config.websocket_port}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            self.config.enable_websocket = False
    
    async def _stop_websocket_server(self) -> None:
        """Stop WebSocket server."""
        if self._websocket_server:
            await self._websocket_server.stop()
            self._websocket_server = None
            logger.info("WebSocket server stopped")
    
    def get_position_summary(self, symbol: str = None) -> Dict:
        """
        Get position summary.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Dict with position summary
        """
        positions = self.portfolio.positions.values()
        
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        
        if not positions:
            return {
                "count": 0,
                "long_count": 0,
                "short_count": 0,
                "total_volume": 0,
                "total_pnl": 0,
                "long_exposure": 0,
                "short_exposure": 0
            }
        
        long_positions = [p for p in positions if p.is_long]
        short_positions = [p for p in positions if p.is_short]
        
        return {
            "count": len(positions),
            "long_count": len(long_positions),
            "short_count": len(short_positions),
            "total_volume": sum(p.volume for p in positions),
            "total_pnl": sum(p.pnl for p in positions),
            "long_exposure": sum(p.current_value for p in long_positions),
            "short_exposure": sum(p.current_value for p in short_positions),
            "positions": [p.to_dict() for p in positions]
        }
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """
        Get performance summary.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with performance metrics
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        stats = self.portfolio.calculate_statistics(period_start=cutoff_date)
        
        return {
            "period_days": days,
            "period_start": cutoff_date.isoformat(),
            "trades": stats["total_trades"],
            "win_rate": stats["win_rate"],
            "profit_factor": stats["profit_factor"],
            "expectancy": stats["expectancy"],
            "avg_win": stats["avg_win"],
            "avg_loss": stats["avg_loss"],
            "max_win": stats["max_win"],
            "max_loss": stats["max_loss"],
            "net_pnl": stats.get("net_pnl", 0),
            "avg_trade_duration_hours": stats.get("avg_trade_duration_hours", 0)
        }


class PortfolioWebSocketServer:
    """
    WebSocket server for real-time portfolio updates.
    """
    
    def __init__(
        self,
        port: int = 8765,
        monitor: PortfolioMonitor = None
    ):
        self.port = port
        self.monitor = monitor
        self.clients: Set = set()
        self._server = None
        self._running = False
    
    async def start(self) -> None:
        """Start WebSocket server."""
        try:
            import websockets
            import asyncio
            
            self._running = True
            self._server = await websockets.serve(
                self._handle_client,
                "0.0.0.0",
                self.port
            )
            logger.info(f"WebSocket server listening on ws://0.0.0.0:{self.port}")
            
        except ImportError:
            logger.warning("WebSocket server requires 'websockets' package")
            logger.info("Install with: pip install websockets")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
    
    async def stop(self) -> None:
        """Stop WebSocket server."""
        self._running = False
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        for client in list(self.clients):
            await client.close()
        
        logger.info("WebSocket server stopped")
    
    async def _handle_client(self, websocket) -> None:
        """Handle client connection."""
        self.clients.add(websocket)
        client_info = f"{websocket.remote_address}"
        logger.info(f"Client connected: {client_info}")
        
        try:
            async for message in websocket:
                await self._process_message(websocket, message)
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client disconnected: {client_info}")
    
    async def _process_message(self, websocket, message: str) -> None:
        """Process client message."""
        try:
            import json
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "subscribe":
                await self._send_snapshot(websocket)
            elif msg_type == "get_snapshot":
                await self._send_snapshot(websocket)
            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError:
            logger.warning("Invalid JSON message received")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _send_snapshot(self, websocket) -> None:
        """Send portfolio snapshot to client."""
        if self.monitor:
            snapshot = self.monitor.get_portfolio_snapshot()
            import json
            await websocket.send(json.dumps({
                "type": "snapshot",
                "data": snapshot
            }))
    
    async def broadcast_portfolio(self, portfolio: Portfolio) -> None:
        """
        Broadcast portfolio update to all clients.
        
        Args:
            portfolio: Portfolio to broadcast
        """
        if not self.clients or not self._running:
            return
        
        try:
            import json
            import asyncio
            
            snapshot = self.monitor.get_portfolio_snapshot()
            message = json.dumps({
                "type": "portfolio_update",
                "data": snapshot
            })
            
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}")


async def run_monitor_demo() -> None:
    """Run a demo of the portfolio monitor."""
    monitor = PortfolioMonitor()
    
    monitor.subscribe(
        lambda portfolio, update_type, data: print(f"Update: {update_type}")
    )
    
    await monitor.start()
    
    try:
        while True:
            await asyncio.sleep(10)
            snapshot = monitor.get_portfolio_snapshot()
            print(f"Positions: {snapshot['position_count']}, Equity: ${snapshot['account']['equity']:,.2f}")
    except KeyboardInterrupt:
        await monitor.stop()


if __name__ == "__main__":
    asyncio.run(run_monitor_demo())
