"""
⚡ QUANTA AI - Multi-Agent Framework
====================================
Advanced multi-agent system for autonomous trading with
message passing, state management, and agent coordination.

Author: Quanta AI Team
Version: 2.0.0
"""

import uuid
import time
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Type
from enum import Enum
from datetime import datetime
from collections import defaultdict, deque
import json
import hashlib


class AgentState(Enum):
    """Agent lifecycle states."""
    CREATED = "created"
    INITIALIZING = "initializing"
    IDLE = "idle"
    RUNNING = "running"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class AgentType(Enum):
    """Agent type classifications."""
    DATA = "data"
    COGNITIVE = "cognitive"
    STRATEGIC = "strategic"
    EXECUTIVE = "executive"
    RISK = "risk"
    MONITORING = "monitoring"
    LEARNING = "learning"


class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = 0    # Immediate processing
    HIGH = 1        # Process soon
    NORMAL = 2      # Standard priority
    LOW = 3         # Background processing
    BACKGROUND = 4  # Can wait


class MessageType(Enum):
    """Agent message types."""
    # Data messages
    DATA_REQUEST = "data_request"
    DATA_RESPONSE = "data_response"
    DATA_UPDATE = "data_update"
    
    # Analysis messages
    ANALYSIS_REQUEST = "analysis_request"
    ANALYSIS_RESPONSE = "analysis_response"
    PATTERN_DETECTED = "pattern_detected"
    
    # Strategy messages
    SIGNAL_GENERATED = "signal_generated"
    STRATEGY_UPDATE = "strategy_update"
    REGIME_CHANGE = "regime_change"
    
    # Trading messages
    ORDER_REQUEST = "order_request"
    ORDER_RESPONSE = "order_response"
    POSITION_UPDATE = "position_update"
    
    # Risk messages
    RISK_ASSESSMENT = "risk_assessment"
    RISK_ALERT = "risk_alert"
    LIMIT_WARNING = "limit_warning"
    
    # System messages
    HEARTBEAT = "heartbeat"
    STATUS_REPORT = "status_report"
    SHUTDOWN = "shutdown"
    CONFIG_UPDATE = "config_update"
    
    # Coordination messages
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETE = "task_complete"
    CONSENSUS_REQUEST = "consensus_request"
    CONSENSUS_RESPONSE = "consensus_response"


@dataclass
class AgentMessage:
    """Message format for agent communication."""
    msg_type: MessageType
    sender_id: str
    receiver_id: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None
    requires_acknowledgment: bool = False
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'msg_type': self.msg_type.value,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'message_id': self.message_id,
            'priority': self.priority.value,
            'correlation_id': self.correlation_id,
            'requires_acknowledgment': self.requires_acknowledgment
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        return cls(
            msg_type=MessageType(data['msg_type']),
            sender_id=data['sender_id'],
            receiver_id=data['receiver_id'],
            payload=data['payload'],
            timestamp=data.get('timestamp', time.time()),
            message_id=data.get('message_id', str(uuid.uuid4())),
            priority=MessagePriority(data.get('priority', 'normal')),
            correlation_id=data.get('correlation_id'),
            requires_acknowledgment=data.get('requires_acknowledgment', False)
        )
    
    def get_hash(self) -> str:
        """Generate message hash for deduplication."""
        content = f"{self.msg_type.value}:{self.sender_id}:{self.receiver_id}:{self.timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


@dataclass
class AgentPerformance:
    """Agent performance metrics."""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0
    last_activity: float = field(default_factory=time.time)
    average_response_time: float = 0.0
    error_rate: float = 0.0
    success_rate: float = 1.0
    
    def update(self, success: bool, processing_time: float) -> None:
        """Update metrics."""
        self.last_activity = time.time()
        self.total_processing_time += processing_time
        
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
        
        total = self.tasks_completed + self.tasks_failed
        if total > 0:
            self.success_rate = self.tasks_completed / total
            self.error_rate = self.tasks_failed / total
        
        if self.tasks_completed > 0:
            self.average_response_time = self.total_processing_time / self.tasks_completed


class BaseAgent(ABC):
    """Base class for all agents in the Quanta system."""
    
    def __init__(self, agent_id: str, name: str, agent_type: AgentType = AgentType.COGNITIVE):
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type
        self.state = AgentState.CREATED
        self.logger = logging.getLogger(f"Quanta.{name}")
        self.message_queue: deque = deque(maxlen=1000)
        self.subscriptions: set = set()
        self.capabilities: List[str] = []
        self.performance = AgentPerformance()
        self.last_heartbeat = time.time()
        self.config: Dict[str, Any] = {}
        self.acknowledgments: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._running = False
        self._processing = False
        
    @property
    def is_alive(self) -> bool:
        """Check if agent is alive."""
        return (time.time() - self.last_heartbeat) < 30.0
    
    @property
    def is_busy(self) -> bool:
        """Check if agent is processing."""
        return self._processing
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize agent with configuration."""
        with self._lock:
            self.config.update(config)
            self.state = AgentState.INITIALIZING
            success = self._initialize_impl()
            if success:
                self.state = AgentState.IDLE
                self.logger.info(f"Agent {self.name} initialized successfully")
            else:
                self.state = AgentState.ERROR
                self.logger.error(f"Agent {self.name} initialization failed")
            return success
    
    @abstractmethod
    def _initialize_impl(self) -> bool:
        """Implementation-specific initialization."""
        pass
    
    def start(self) -> bool:
        """Start the agent."""
        with self._lock:
            if self.state == AgentState.SHUTDOWN:
                self.logger.warning(f"Agent {self.name} is shutdown, cannot start")
                return False
            
            self._running = True
            self.state = AgentState.RUNNING
            self.logger.info(f"Agent {self.name} started")
            return True
    
    def stop(self) -> bool:
        """Stop the agent."""
        with self._lock:
            self._running = False
            self.state = AgentState.IDLE
            self.logger.info(f"Agent {self.name} stopped")
            return True
    
    def shutdown(self) -> None:
        """Shutdown the agent permanently."""
        with self._lock:
            self._running = False
            self.state = AgentState.SHUTDOWN
            # Clear message queue
            self.message_queue.clear()
            self.logger.info(f"Agent {self.name} shutdown")
    
    def pause(self) -> bool:
        """Pause the agent."""
        with self._lock:
            if self._running:
                self.state = AgentState.PAUSED
                self.logger.info(f"Agent {self.name} paused")
                return True
            return False
    
    def resume(self) -> bool:
        """Resume the agent."""
        with self._lock:
            if self.state == AgentState.PAUSED:
                self.state = AgentState.RUNNING
                self.logger.info(f"Agent {self.name} resumed")
                return True
            return False
    
    def subscribe(self, msg_type: MessageType) -> None:
        """Subscribe to message type."""
        with self._lock:
            self.subscriptions.add(msg_type)
    
    def unsubscribe(self, msg_type: MessageType) -> None:
        """Unsubscribe from message type."""
        with self._lock:
            self.subscriptions.discard(msg_type)
    
    def send_message(self, message: AgentMessage, delay: float = 0) -> bool:
        """Send message to another agent."""
        start_time = time.time()
        success = False
        
        try:
            if delay > 0:
                timer = threading.Timer(delay, self._deliver_message, args=[message])
                timer.start()
            else:
                success = self._deliver_message(message)
            
            with self._lock:
                self.performance.messages_sent += 1
                
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            success = False
        
        finally:
            processing_time = time.time() - start_time
            self.performance.update(success, processing_time)
        
        return success
    
    def _deliver_message(self, message: AgentMessage) -> bool:
        """Internal method to deliver message."""
        # This will be overridden by the agent coordinator
        return True
    
    def receive_message(self, message: AgentMessage) -> bool:
        """Receive message from another agent."""
        start_time = time.time()
        success = False
        
        try:
            with self._lock:
                self.message_queue.append(message)
                self.performance.messages_received += 1
            
            success = self._process_message(message)
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            success = False
        
        finally:
            processing_time = time.time() - start_time
            self.performance.update(success, processing_time)
        
        return success
    
    @abstractmethod
    def _process_message(self, message: AgentMessage) -> bool:
        """Process incoming message. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute main task. Must be implemented by subclasses."""
        pass
    
    def heartbeat(self) -> None:
        """Send heartbeat."""
        self.last_heartbeat = time.time()
    
    def acknowledge(self, message_id: str) -> None:
        """Acknowledge a message."""
        with self._lock:
            self.acknowledgments[message_id] = time.time()
    
    def get_pending_acknowledgments(self) -> List[str]:
        """Get messages awaiting acknowledgment."""
        timeout = time.time() - 30  # 30 seconds timeout
        return [
            msg_id for msg_id, timestamp in self.acknowledgments.items()
            if timestamp > timeout
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        queue_size = len(self.message_queue)
        
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'type': self.agent_type.value,
            'state': self.state.value,
            'is_alive': self.is_alive,
            'is_busy': self.is_busy,
            'message_queue_size': queue_size,
            'subscriptions': [m.value for m in self.subscriptions],
            'capabilities': self.capabilities,
            'performance': {
                'tasks_completed': self.performance.tasks_completed,
                'tasks_failed': self.performance.tasks_failed,
                'success_rate': f"{self.performance.success_rate:.2%}",
                'average_response_time': f"{self.performance.average_response_time:.3f}s",
                'messages_sent': self.performance.messages_sent,
                'messages_received': self.performance.messages_received,
            },
            'last_heartbeat': self.last_heartbeat,
            'config': self.config
        }
    
    def get_state(self) -> Dict[str, Any]:
        """Get agent state for serialization."""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'state': self.state.value,
            'config': self.config,
            'performance': {
                'tasks_completed': self.performance.tasks_completed,
                'success_rate': self.performance.success_rate,
            }
        }
    
    def load_state(self, state: Dict[str, Any]) -> None:
        """Load agent state from serialization."""
        if 'config' in state:
            self.config.update(state['config'])


class AgentCoordinator:
    """Coordinates communication and execution between agents."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_history: List[AgentMessage] = []
        self.dispatched_messages: Dict[str, AgentMessage] = {}
        self.config = config or {}
        self.logger = logging.getLogger("Quanta.Coordinator")
        self._lock = threading.RLock()
        self._dispatch_table: Dict[MessageType, List[str]] = defaultdict(list)
        self._round_robin: Dict[str, int] = {}
        self._message_stats = {
            'total_messages': 0,
            'delivered': 0,
            'failed': 0,
            'avg_delivery_time': 0.0
        }
        
    def register_agent(self, agent: BaseAgent) -> bool:
        """Register an agent with the coordinator."""
        with self._lock:
            if agent.agent_id in self.agents:
                self.logger.warning(f"Agent {agent.agent_id} already registered")
                return False
            
            self.agents[agent.agent_id] = agent
            
            # Register agent's subscriptions
            for msg_type in agent.subscriptions:
                self._dispatch_table[msg_type].append(agent.agent_id)
                self.logger.debug(f"{agent.name} subscribed to {msg_type.value}")
            
            self._round_robin[agent.agent_id] = 0
            
            self.logger.info(f"Registered agent: {agent.name} ({agent.agent_id})")
            return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        with self._lock:
            if agent_id not in self.agents:
                return False
            
            agent = self.agents[agent_id]
            for msg_type in agent.subscriptions:
                if agent_id in self._dispatch_table[msg_type]:
                    self._dispatch_table[msg_type].remove(agent_id)
            
            if agent_id in self._round_robin:
                del self._round_robin[agent_id]
            
            del self.agents[agent_id]
            self.logger.info(f"Unregistered agent: {agent_id}")
            return True
    
    def send_message(self, message: AgentMessage) -> bool:
        """Send message from one agent to another."""
        start_time = time.time()
        success = False
        
        with self._lock:
            self.message_history.append(message)
            self._message_stats['total_messages'] += 1
            
            # Deliver to receiver
            receiver_id = message.receiver_id
            
            if receiver_id == 'broadcast':
                success = self._broadcast_message(message)
            elif receiver_id in self.agents:
                agent = self.agents[receiver_id]
                threading.Thread(
                    target=agent.receive_message, 
                    args=(message,),
                    daemon=True
                ).start()
                success = True
                self._message_stats['delivered'] += 1
            else:
                self.logger.warning(f"Unknown agent: {receiver_id}")
                self._message_stats['failed'] += 1
            
            # Update stats
            delivery_time = time.time() - start_time
            self._update_delivery_stats(delivery_time, success)
        
        return success
    
    def _broadcast_message(self, message: AgentMessage) -> bool:
        """Broadcast message to all subscribers."""
        success = True
        msg_type = message.msg_type
        
        for agent_id in self._dispatch_table.get(msg_type, list(self.agents.keys())):
            if agent_id != message.sender_id:
                msg = AgentMessage(
                    msg_type=message.msg_type,
                    sender_id=message.sender_id,
                    receiver_id=agent_id,
                    payload=message.payload.copy(),
                    priority=message.priority,
                    correlation_id=message.correlation_id
                )
                if agent_id in self.agents:
                    threading.Thread(
                        target=self.agents[agent_id].receive_message,
                        args=(msg,),
                        daemon=True
                    ).start()
                else:
                    success = False
        
        return success
    
    def route_message(self, message: AgentMessage) -> int:
        """Route message to appropriate agents. Returns number of recipients."""
        recipients = 0
        
        with self._lock:
            # Check direct recipient first
            if message.receiver_id and message.receiver_id in self.agents:
                self.send_message(message)
                return 1
            
            # Route to subscribers using round-robin
            msg_t = message.msg_type
            agent_ids = self._dispatch_table.get(msg_t, [])
            
            if not agent_ids:
                # No direct subscribers, broadcast to all
                agent_ids = list(self.agents.keys())
            
            for agent_id in agent_ids:
                if agent_id != message.sender_id:
                    msg = AgentMessage(
                        msg_type=message.msg_type,
                        sender_id=message.sender_id,
                        receiver_id=agent_id,
                        payload=message.payload.copy(),
                        priority=message.priority,
                        correlation_id=message.correlation_id
                    )
                    self.send_message(msg)
                    recipients += 1
        
        return recipients
    
    def _update_delivery_stats(self, delivery_time: float, success: bool) -> None:
        """Update delivery statistics."""
        count = self._message_stats['delivered'] + self._message_stats['failed']
        if count > 0:
            self._message_stats['avg_delivery_time'] = (
                (self._message_stats['avg_delivery_time'] * (count - 1) + delivery_time) / count
            )
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get status of all agents."""
        return [agent.get_status() for agent in self.agents.values()]
    
    def get_coordinator_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        return {
            'registered_agents': len(self.agents),
            'total_messages': self._message_stats['total_messages'],
            'delivered': self._message_stats['delivered'],
            'failed': self._message_stats['failed'],
            'avg_delivery_time': f"{self._message_stats['avg_delivery_time']:.4f}s",
            'message_history_size': len(self.message_history)
        }
    
    def shutdown_all(self) -> None:
        """Shutdown all agents gracefully."""
        for agent in list(self.agents.values()):
            agent.shutdown()
        self.logger.info("All agents shutdown")
    
    def get_message_history(self, msg_type: MessageType = None, 
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Get message history."""
        messages = self.message_history
        
        if msg_type:
            messages = [m for m in messages if m.msg_type == msg_type]
        
        messages = messages[-limit:]
        
        return [m.to_dict() for m in messages]
