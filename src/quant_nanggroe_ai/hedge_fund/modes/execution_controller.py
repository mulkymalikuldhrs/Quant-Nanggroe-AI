"""
Execution Controller for AI Quant Hedge Fund
Handles trade execution based on trading mode
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status of trade execution."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ExecutionReason(Enum):
    """Reason for execution status."""
    SIGNAL = "signal"
    USER_CONFIRMATION = "user_confirmation"
    AUTO_APPROVAL = "auto_approval"
    RISK_LIMIT = "risk_limit"
    MANUAL_CANCEL = "manual_cancel"
    ERROR = "error"


@dataclass
class TradeProposal:
    """Proposed trade from analysis engine."""
    timestamp: datetime
    symbol: str
    side: str
    volume: float
    entry_price: float
    sl: Optional[float]
    tp: Optional[float]
    confidence: float
    strategy: str
    reasoning: List[str]
    metadata: Dict = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    order_id: str = None
    
    def __post_init__(self):
        if self.order_id is None:
            self.order_id = str(uuid.uuid4())[:8]
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_buy(self) -> bool:
        return self.side.upper() == "BUY"
    
    @property
    def is_sell(self) -> bool:
        return self.side.upper() == "SELL"
    
    @property
    def risk_reward_ratio(self) -> float:
        if self.sl is None or self.tp is None:
            return 0.0
        sl_dist = abs(self.entry_price - self.sl)
        tp_dist = abs(self.tp - self.entry_price)
        if sl_dist == 0:
            return 0.0
        return tp_dist / sl_dist
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "side": self.side,
            "volume": self.volume,
            "entry_price": self.entry_price,
            "sl": self.sl,
            "tp": self.tp,
            "confidence": self.confidence,
            "strategy": self.strategy,
            "reasoning": self.reasoning,
            "status": self.status.value,
            "risk_reward_ratio": self.risk_reward_ratio,
            "metadata": self.metadata
        }


@dataclass
class ExecutionResult:
    """Result of trade execution."""
    order_id: str
    status: ExecutionStatus
    reason: ExecutionReason
    timestamp: datetime
    broker_response: Dict = None
    error_message: str = None
    execution_price: float = None
    execution_volume: float = None
    commission: float = 0.0
    slippage: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "status": self.status.value,
            "reason": self.reason.value,
            "timestamp": self.timestamp.isoformat(),
            "execution_price": self.execution_price,
            "execution_volume": self.execution_volume,
            "commission": self.commission,
            "slippage": self.slippage,
            "error_message": self.error_message,
            "broker_response": self.broker_response
        }


class ExecutionController:
    """
    Controller for trade execution based on trading mode.
    
    Features:
    - Mode-aware execution
    - Risk management
    - Order queuing for confirmation
    - Execution callbacks
    - Statistics tracking
    """
    
    def __init__(
        self,
        mode_manager,
        broker=None,
        notifier=None,
        risk_manager=None
    ):
        self.mode_manager = mode_manager
        self.broker = broker
        self.notifier = notifier
        self.risk_manager = risk_manager
        
        self._pending_proposals: Dict[str, TradeProposal] = {}
        self._executed_trades: List[ExecutionResult] = []
        self._cancelled_trades: List[ExecutionResult] = []
        self._rejected_trades: List[ExecutionResult] = []
        
        self._execution_callbacks: List[Callable] = []
        self._confirmation_callbacks: List[Callable] = []
        
        self._setup_callbacks()
    
    def _setup_callbacks(self) -> None:
        """Setup mode manager callbacks."""
        self.mode_manager.add_callback(self._on_mode_change)
    
    def add_execution_callback(self, callback: Callable) -> None:
        """Add callback for execution events."""
        self._execution_callbacks.append(callback)
    
    def add_confirmation_callback(self, callback: Callable) -> None:
        """Add callback for confirmation requests."""
        self._confirmation_callbacks.append(callback)
    
    async def process_signal(self, proposal: TradeProposal) -> ExecutionResult:
        """
        Process a trading signal based on current mode.
        
        Args:
            proposal: Trade proposal from analysis
            
        Returns:
            ExecutionResult with execution status
        """
        mode = self.mode_manager.current_mode
        logger.info(f"Processing signal: {proposal.symbol} {proposal.side} {proposal.confidence:.0%} (mode: {mode.value})")
        
        if mode.value == "manual":
            return await self._handle_manual(proposal)
        elif mode.value == "semi_auto":
            return await self._handle_semi_auto(proposal)
        elif mode.value == "full_auto":
            return await self._handle_full_auto(proposal)
        else:
            return ExecutionResult(
                order_id=proposal.order_id,
                status=ExecutionStatus.REJECTED,
                reason=ExecutionReason.ERROR,
                timestamp=datetime.now(),
                error_message=f"Unknown mode: {mode.value}"
            )
    
    async def _handle_manual(self, proposal: TradeProposal) -> ExecutionResult:
        """Manual mode: Notify user, wait for manual action."""
        self._pending_proposals[proposal.order_id] = proposal
        
        if self.notifier:
            await self.notifier.notify_trade_proposal(proposal)
        
        self._notify_confirmation_callbacks(proposal)
        
        logger.info(f"Signal queued for manual action: {proposal.order_id}")
        
        return ExecutionResult(
            order_id=proposal.order_id,
            status=ExecutionStatus.PENDING,
            reason=ExecutionReason.SIGNAL,
            timestamp=datetime.now()
        )
    
    async def _handle_semi_auto(self, proposal: TradeProposal) -> ExecutionResult:
        """Semi-auto mode: Auto-approve high confidence signals."""
        confidence = proposal.confidence
        
        if self.mode_manager.should_auto_approve(confidence):
            logger.info(f"Auto-approving high confidence signal: {confidence:.0%}")
            return await self._execute_trade(proposal, ExecutionReason.AUTO_APPROVAL)
        else:
            self._pending_proposals[proposal.order_id] = proposal
            
            if self.notifier:
                await self.notifier.request_confirmation(proposal)
            
            self._notify_confirmation_callbacks(proposal)
            
            logger.info(f"Waiting for confirmation: {proposal.order_id}")
            
            return ExecutionResult(
                order_id=proposal.order_id,
                status=ExecutionStatus.PENDING,
                reason=ExecutionReason.SIGNAL,
                timestamp=datetime.now()
            )
    
    async def _handle_full_auto(self, proposal: TradeProposal) -> ExecutionResult:
        """Full auto mode: Execute immediately after risk check."""
        allowed, reason = self.mode_manager.is_execution_allowed(
            confidence=proposal.confidence,
            position_size=proposal.volume,
            current_daily_loss=0.0
        )
        
        if not allowed:
            logger.warning(f"Execution rejected by risk limits: {reason}")
            return ExecutionResult(
                order_id=proposal.order_id,
                status=ExecutionStatus.REJECTED,
                reason=ExecutionReason.RISK_LIMIT,
                timestamp=datetime.now(),
                error_message=reason
            )
        
        return await self._execute_trade(proposal, ExecutionReason.SIGNAL)
    
    async def confirm_proposal(
        self,
        order_id: str,
        confirmed: bool,
        modified_volume: float = None
    ) -> ExecutionResult:
        """
        Confirm or reject a pending proposal.
        
        Args:
            order_id: Proposal order ID
            confirmed: True to confirm, False to reject
            modified_volume: Optional modified volume
            
        Returns:
            ExecutionResult
        """
        proposal = self._pending_proposals.get(order_id)
        
        if proposal is None:
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.FAILED,
                reason=ExecutionReason.ERROR,
                timestamp=datetime.now(),
                error_message="Proposal not found"
            )
        
        if not confirmed:
            del self._pending_proposals[order_id]
            
            result = ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.CANCELLED,
                reason=ExecutionReason.MANUAL_CANCEL,
                timestamp=datetime.now()
            )
            self._cancelled_trades.append(result)
            
            logger.info(f"Proposal cancelled: {order_id}")
            return result
        
        if modified_volume and modified_volume != proposal.volume:
            proposal.volume = modified_volume
            logger.info(f"Volume modified: {order_id} {proposal.volume}")
        
        return await self._execute_trade(proposal, ExecutionReason.USER_CONFIRMATION)
    
    async def _execute_trade(
        self,
        proposal: TradeProposal,
        reason: ExecutionReason
    ) -> ExecutionResult:
        """Execute the trade via broker."""
        try:
            if self.broker is None:
                return ExecutionResult(
                    order_id=proposal.order_id,
                    status=ExecutionStatus.REJECTED,
                    reason=ExecutionReason.ERROR,
                    timestamp=datetime.now(),
                    error_message="No broker configured"
                )
            
            result = self.broker.place_order(
                symbol=proposal.symbol,
                action=proposal.side,
                volume=proposal.volume,
                stop_loss=proposal.sl,
                take_profit=proposal.tp
            )
            
            if result.get("success"):
                proposal.status = ExecutionStatus.EXECUTED
                
                execution_result = ExecutionResult(
                    order_id=proposal.order_id,
                    status=ExecutionStatus.EXECUTED,
                    reason=reason,
                    timestamp=datetime.now(),
                    broker_response=result,
                    execution_price=result.get("price"),
                    execution_volume=result.get("volume")
                )
                
                self._executed_trades.append(execution_result)
                self._notify_execution_callbacks(proposal, execution_result)
                
                logger.info(f"Trade executed: {proposal.symbol} {proposal.side} {proposal.volume} @ {result.get('price')}")
                
                return execution_result
            else:
                proposal.status = ExecutionStatus.FAILED
                
                execution_result = ExecutionResult(
                    order_id=proposal.order_id,
                    status=ExecutionStatus.FAILED,
                    reason=ExecutionReason.ERROR,
                    timestamp=datetime.now(),
                    broker_response=result,
                    error_message=result.get("error", "Unknown error")
                )
                
                self._rejected_trades.append(execution_result)
                
                logger.error(f"Trade failed: {proposal.symbol} - {result.get('error')}")
                
                return execution_result
                
        except Exception as e:
            logger.error(f"Execution error: {e}")
            
            result = ExecutionResult(
                order_id=proposal.order_id,
                status=ExecutionStatus.FAILED,
                reason=ExecutionReason.ERROR,
                timestamp=datetime.now(),
                error_message=str(e)
            )
            
            self._rejected_trades.append(result)
            return result
    
    def cancel_proposal(self, order_id: str) -> bool:
        """
        Cancel a pending proposal.
        
        Args:
            order_id: Proposal order ID
            
        Returns:
            bool: True if cancelled
        """
        if order_id in self._pending_proposals:
            del self._pending_proposals[order_id]
            logger.info(f"Proposal cancelled: {order_id}")
            return True
        return False
    
    def get_pending_proposals(self) -> List[TradeProposal]:
        """Get all pending proposals."""
        return list(self._pending_proposals.values())
    
    def get_execution_statistics(self) -> Dict:
        """Get execution statistics."""
        total = len(self._executed_trades) + len(self._rejected_trades) + len(self._cancelled_trades)
        
        executed = len(self._executed_trades)
        rejected = len(self._rejected_trades)
        cancelled = len(self._cancelled_trades)
        pending = len(self._pending_proposals)
        
        return {
            "total_signals": total,
            "executed": executed,
            "rejected": rejected,
            "cancelled": cancelled,
            "pending": pending,
            "execution_rate": executed / total if total > 0 else 0,
            "rejection_rate": rejected / total if total > 0 else 0,
            "cancellation_rate": cancelled / total if total > 0 else 0
        }
    
    def _notify_execution_callbacks(
        self,
        proposal: TradeProposal,
        result: ExecutionResult
    ) -> None:
        """Notify execution callbacks."""
        for callback in self._execution_callbacks:
            try:
                callback(proposal, result)
            except Exception as e:
                logger.error(f"Execution callback error: {e}")
    
    def _notify_confirmation_callbacks(self, proposal: TradeProposal) -> None:
        """Notify confirmation callbacks."""
        for callback in self._confirmation_callbacks:
            try:
                callback(proposal)
            except Exception as e:
                logger.error(f"Confirmation callback error: {e}")
    
    def _on_mode_change(
        self,
        from_mode: str,
        to_mode: str,
        config: Dict,
        emergency_stop: bool = False
    ) -> None:
        """Handle mode change."""
        logger.info(f"Execution controller mode change: {from_mode} -> {to_mode}")
        
        if emergency_stop:
            for order_id in list(self._pending_proposals.keys()):
                self.cancel_proposal(order_id)
            logger.info("All pending proposals cancelled due to emergency stop")
    
    def close_all_positions(self) -> List[ExecutionResult]:
        """
        Close all open positions.
        
        Returns:
            List of execution results
        """
        if self.broker is None:
            return []
        
        results = []
        positions = self.broker.get_positions()
        
        for pos in positions:
            result = self.broker.close_position(pos["ticket"])
            
            execution_result = ExecutionResult(
                order_id=f"CLOSE_{pos['ticket']}",
                status=ExecutionStatus.EXECUTED if result.get("success") else ExecutionStatus.FAILED,
                reason=ExecutionReason.MANUAL_CANCEL,
                timestamp=datetime.now(),
                broker_response=result
            )
            
            results.append(execution_result)
        
        logger.info(f"Closed {len(results)} positions")
        return results


class Notifier:
    """
    Placeholder notifier for trade notifications.
    Can be extended to support Telegram, Email, Slack, etc.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
    
    async def notify_trade_proposal(self, proposal: TradeProposal) -> None:
        """Notify of new trade proposal."""
        logger.info(f"[NOTIFICATION] New trade proposal: {proposal.symbol} {proposal.side}")
    
    async def request_confirmation(self, proposal: TradeProposal) -> None:
        """Request user confirmation."""
        logger.info(f"[NOTIFICATION] Confirmation requested: {proposal.order_id}")
    
    async def notify_execution(
        self,
        proposal: TradeProposal,
        result: ExecutionResult
    ) -> None:
        """Notify of trade execution."""
        status = "EXECUTED" if result.status == ExecutionStatus.EXECUTED else "FAILED"
        logger.info(f"[NOTIFICATION] Trade {status}: {proposal.symbol} {proposal.side}")


def create_execution_controller(
    mode="semi_auto",
    broker=None
) -> ExecutionController:
    """
    Factory function to create execution controller.
    
    Args:
        mode: Initial mode (string or ModeManager instance)
        broker: Broker instance
        
    Returns:
        ExecutionController instance
    """
    from src.modes.mode_manager import create_mode_manager, ModeManager
    
    if isinstance(mode, ModeManager):
        mode_manager = mode
    else:
        mode_manager = create_mode_manager(mode)
    
    notifier = Notifier()
    
    return ExecutionController(
        mode_manager=mode_manager,
        broker=broker,
        notifier=notifier
    )
