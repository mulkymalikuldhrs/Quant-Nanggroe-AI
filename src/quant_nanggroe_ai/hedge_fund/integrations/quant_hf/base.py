"""
🌟 ORCHID QUANTUM AI - Multi-Agent Framework
==============================================
Base classes for the multi-agent trading system.
"""

import uuid
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from datetime import datetime
import threading
import json
from collections import defaultdict


class AgentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"


class MessageType(Enum):
    DATA_REQUEST = "data_request"
    DATA_RESPONSE = "data_response"
    ANALYSIS_REQUEST = "analysis_request"
    ANALYSIS_RESPONSE = "analysis_response"
    TRADING_SIGNAL = "trading_signal"
    RISK_ALERT = "risk_alert"
    HEARTBEAT = "heartbeat"
    SHUTDOWN = "shutdown"
    COORDINATION = "coordination"


@dataclass
class AgentMessage:
    """Message format for agent communication."""
    msg_type: MessageType
    sender_id: str
    receiver_id: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = 0
    requires_acknowledgment: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'msg_type': self.msg_type.value,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'message_id': self.message_id,
            'priority': self.priority,
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
            priority=data.get('priority', 0),
            requires_acknowledgment=data.get('requires_acknowledgment', False)
        )


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.state = AgentState.IDLE
        self.logger = logging.getLogger(f"Agent.{name}")
        self.message_queue: List[AgentMessage] = []
        self.subscriptions: List[MessageType] = []
        self.capabilities: List[str] = []
        self.performance_metrics: Dict[str, float] = {}
        self.last_heartbeat = time.time()
        self.acknowledgments: Dict[str, bool] = {}
        self._lock = threading.Lock()
        self._running = False
        
    @property
    def is_alive(self) -> bool:
        """Check if agent is alive."""
        return (time.time() - self.last_heartbeat) < 30.0
    
    def start(self) -> None:
        """Start the agent."""
        with self._lock:
            self._running = True
            self.state = AgentState.RUNNING
            self.logger.info(f"Agent {self.name} started")
    
    def stop(self) -> None:
        """Stop the agent."""
        with self._lock:
            self._running = False
            self.state = AgentState.IDLE
            self.logger.info(f"Agent {self.name} stopped")
    
    def subscribe(self, msg_type: MessageType) -> None:
        """Subscribe to message type."""
        if msg_type not in self.subscriptions:
            self.subscriptions.append(msg_type)
    
    def unsubscribe(self, msg_type: MessageType) -> None:
        """Unsubscribe from message type."""
        if msg_type in self.subscriptions:
            self.subscriptions.remove(msg_type)
    
    def send_message(self, message: AgentMessage, delay: float = 0) -> None:
        """Send message to another agent."""
        if delay > 0:
            timer = threading.Timer(delay, self._deliver_message, args=[message])
            timer.start()
        else:
            self._deliver_message(message)
    
    def _deliver_message(self, message: AgentMessage) -> None:
        """Internal method to deliver message."""
        # This will be overridden by the agent coordinator
        pass
    
    def receive_message(self, message: AgentMessage) -> None:
        """Receive message from another agent."""
        with self._lock:
            self.message_queue.append(message)
        
        self._process_message(message)
    
    @abstractmethod
    def _process_message(self, message: AgentMessage) -> None:
        """Process incoming message. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize agent with configuration."""
        pass
    
    @abstractmethod
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute main task. Must be implemented by subclasses."""
        pass
    
    def heartbeat(self) -> None:
        """Send heartbeat."""
        self.last_heartbeat = time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'state': self.state.value,
            'is_alive': self.is_alive,
            'message_queue_size': len(self.message_queue),
            'capabilities': self.capabilities,
            'performance': self.performance_metrics,
            'last_heartbeat': self.last_heartbeat
        }
    
    def acknowledge(self, message_id: str) -> None:
        """Acknowledge a message."""
        self.acknowledgments[message_id] = True
    
    def get_pending_acknowledgments(self) -> List[str]:
        """Get messages awaiting acknowledgment."""
        return [msg_id for msg_id, acked in self.acknowledgments.items() if not acked]


class AgentCoordinator:
    """Coordinates communication between agents."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_history: List[AgentMessage] = []
        self.config = config or {}
        self.logger = logging.getLogger("Coordinator")
        self._lock = threading.Lock()
        self._dispatch_table: Dict[MessageType, List[str]] = defaultdict(list)
        
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
            
            del self.agents[agent_id]
            self.logger.info(f"Unregistered agent: {agent_id}")
            return True
    
    def send_message(self, message: AgentMessage) -> bool:
        """Send message from one agent to another."""
        with self._lock:
            self.message_history.append(message)
            
            # Deliver to receiver
            receiver_id = message.receiver_id
            if receiver_id in self.agents:
                agent = self.agents[receiver_id]
                threading.Thread(target=agent.receive_message, args=(message,)).start()
                return True
            
            self.logger.warning(f"Unknown agent: {receiver_id}")
            return False
    
    def broadcast_message(self, message: AgentMessage, msg_type: MessageType = None) -> None:
        """Broadcast message to all agents."""
        msg_t = msg_type or message.msg_type
        
        with self._lock:
            for agent_id in self._dispatch_table.get(msg_t, list(self.agents.keys())):
                if agent_id != message.sender_id:
                    msg = AgentMessage(
                        msg_type=message.msg_type,
                        sender_id=message.sender_id,
                        receiver_id=agent_id,
                        payload=message.payload.copy(),
                        priority=message.priority
                    )
                    self.send_message(msg)
    
    def route_message(self, message: AgentMessage) -> None:
        """Route message based on type and subscriptions."""
        # Check direct recipient first
        if message.receiver_id and message.receiver_id in self.agents:
            self.send_message(message)
            return
        
        # Route to subscribers
        for agent_id in self._dispatch_table.get(message.msg_type, []):
            if agent_id != message.sender_id:
                msg = AgentMessage(
                    msg_type=message.msg_type,
                    sender_id=message.sender_id,
                    receiver_id=agent_id,
                    payload=message.payload.copy(),
                    priority=message.priority
                )
                self.send_message(msg)
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get status of all agents."""
        return [agent.get_status() for agent in self.agents.values()]
    
    def shutdown_all(self) -> None:
        """Shutdown all agents."""
        for agent in list(self.agents.values()):
            agent.stop()
        self.logger.info("All agents shutdown")
