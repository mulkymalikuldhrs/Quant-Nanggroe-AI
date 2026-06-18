"""
🔄 Sync Engine - Inter-Agent Communication & Coordination
Real-time synchronization and message passing between agents

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
try:
    import websockets
except ImportError:
    websockets = None
import uuid

class MessageType(Enum):
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    COORDINATION = "coordination"

@dataclass
class Message:
    message_id: str
    from_agent: str
    to_agent: str
    message_type: MessageType
    content: Any
    timestamp: datetime
    priority: int = 5
    requires_response: bool = False
    correlation_id: Optional[str] = None

class SyncEngine:
    """
    Central synchronization engine that manages:
    - Inter-agent communication
    - Message routing and delivery
    - Agent coordination and orchestration
    - Real-time updates and notifications
    - Load balancing and task distribution
    """
    
    def __init__(self):
        self.engine_id = "sync_engine"
        self.status = "initializing"
        
        # Agent registry
        self.registered_agents: Dict[str, Dict] = {}
        self.agent_connections: Dict[str, Any] = {}
        
        # Message queues
        self.message_queues: Dict[str, List[Message]] = {}
        self.pending_responses: Dict[str, Message] = {}
        self.broadcast_subscribers: Dict[str, List[str]] = {}
        
        # Coordination state
        self.active_workflows: Dict[str, Dict] = {}
        self.agent_states: Dict[str, str] = {}
        self.coordination_locks: Dict[str, threading.Lock] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # WebSocket server for real-time communication
        self.websocket_server = None
        self.websocket_port = 8765
        
        # Performance tracking
        self.message_stats = {
            "total_messages": 0,
            "failed_deliveries": 0,
            "avg_latency": 0
        }
        
        self.start_time = time.time()
        self.status = "ready"
    
    async def start(self):
        """Start the sync engine"""
        self.status = "starting"
        
        # Start WebSocket server for real-time communication
        if websockets is not None:
            try:
                self.websocket_server = await websockets.serve(
                    self.handle_websocket_connection,
                    "localhost",
                    self.websocket_port
                )
                print(f"🔄 Sync Engine WebSocket server started on port {self.websocket_port}")
            except Exception as e:
                print(f"⚠️ WebSocket server failed to start: {e}")
        else:
            print("⚠️ websockets package not installed, WebSocket communication disabled")
        
        # Start background tasks
        asyncio.create_task(self.message_processor())
        asyncio.create_task(self.heartbeat_monitor())
        asyncio.create_task(self.cleanup_old_messages())
        
        self.status = "running"
        print("🔄 Sync Engine started successfully")
    
    async def handle_websocket_connection(self, websocket, path):
        """Handle WebSocket connections from agents or UI"""
        connection_id = str(uuid.uuid4())
        try:
            await websocket.send(json.dumps({
                "type": "connection_established",
                "connection_id": connection_id,
                "timestamp": datetime.now().isoformat()
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_websocket_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"WebSocket error: {e}")
    
    async def handle_websocket_message(self, websocket, data):
        """Handle incoming WebSocket messages"""
        message_type = data.get("type")
        
        if message_type == "register_agent":
            agent_id = data.get("agent_id")
            if agent_id:
                self.agent_connections[agent_id] = websocket
                await websocket.send(json.dumps({
                    "type": "registration_success",
                    "agent_id": agent_id
                }))
        
        elif message_type == "send_message":
            message = self.parse_websocket_message(data)
            if message:
                await self.send_message(message)
        
        elif message_type == "get_status":
            status = self.get_engine_status()
            await websocket.send(json.dumps({
                "type": "status_response",
                "status": status
            }))
    
    def register_agent(self, agent_id: str, agent_info: Dict) -> bool:
        """Register an agent with the sync engine"""
        try:
            self.registered_agents[agent_id] = {
                **agent_info,
                "registered_at": datetime.now().isoformat(),
                "last_heartbeat": datetime.now().isoformat(),
                "status": "active"
            }
            
            # Initialize message queue
            if agent_id not in self.message_queues:
                self.message_queues[agent_id] = []
            
            # Initialize agent state
            self.agent_states[agent_id] = "idle"
            
            print(f"✅ Agent {agent_id} registered with sync engine")
            
            # Broadcast agent registration
            self.broadcast_message(
                from_agent="sync_engine",
                message_type=MessageType.STATUS_UPDATE,
                content={"event": "agent_registered", "agent_id": agent_id}
            )
            
            return True
            
        except Exception as e:
            print(f"Error registering agent {agent_id}: {e}")
            return False
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        try:
            if agent_id in self.registered_agents:
                del self.registered_agents[agent_id]
            
            if agent_id in self.agent_connections:
                del self.agent_connections[agent_id]
            
            if agent_id in self.message_queues:
                del self.message_queues[agent_id]
            
            if agent_id in self.agent_states:
                del self.agent_states[agent_id]
            
            # Broadcast agent unregistration
            self.broadcast_message(
                from_agent="sync_engine",
                message_type=MessageType.STATUS_UPDATE,
                content={"event": "agent_unregistered", "agent_id": agent_id}
            )
            
            return True
            
        except Exception as e:
            print(f"Error unregistering agent {agent_id}: {e}")
            return False
    
    async def send_message(self, message: Message) -> bool:
        """Send message to target agent"""
        try:
            # Validate message
            if message.to_agent not in self.registered_agents:
                print(f"Target agent {message.to_agent} not registered")
                return False
            
            # Add to queue
            if message.to_agent not in self.message_queues:
                self.message_queues[message.to_agent] = []
            
            self.message_queues[message.to_agent].append(message)
            
            # Sort by priority (higher priority first)
            self.message_queues[message.to_agent].sort(key=lambda m: m.priority, reverse=True)
            
            # Try immediate delivery via WebSocket
            if message.to_agent in self.agent_connections:
                try:
                    websocket = self.agent_connections[message.to_agent]
                    await websocket.send(json.dumps({
                        "type": "new_message",
                        "message": asdict(message)
                    }, default=str))
                except Exception as e:
                    print(f"WebSocket delivery failed: {e}")
            
            # Update stats
            self.message_stats["total_messages"] += 1
            
            # Store for response tracking
            if message.requires_response:
                self.pending_responses[message.message_id] = message
            
            return True
            
        except Exception as e:
            print(f"Error sending message: {e}")
            self.message_stats["failed_deliveries"] += 1
            return False
    
    def get_messages(self, agent_id: str, limit: int = 10) -> List[Message]:
        """Get pending messages for an agent"""
        if agent_id not in self.message_queues:
            return []
        
        messages = self.message_queues[agent_id][:limit]
        self.message_queues[agent_id] = self.message_queues[agent_id][limit:]
        
        return messages
    
    def _run_async_safely(self, coro):
        """Safely run an async coroutine from a synchronous/thread context"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
        else:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(coro, loop)
                else:
                    loop.run_until_complete(coro)
            except RuntimeError:
                new_loop = asyncio.new_event_loop()
                new_loop.run_until_complete(coro)
                new_loop.close()

    def broadcast_message(self, from_agent: str, message_type: MessageType, 
                         content: Any, exclude_agents: List[str] = None):
        """Broadcast message to all agents"""
        exclude_agents = exclude_agents or []
        
        for agent_id in self.registered_agents:
            if agent_id not in exclude_agents:
                message = Message(
                    message_id=str(uuid.uuid4()),
                    from_agent=from_agent,
                    to_agent=agent_id,
                    message_type=message_type,
                    content=content,
                    timestamp=datetime.now(),
                    priority=3
                )
                
                self._run_async_safely(self.send_message(message))
    
    async def coordinate_workflow(self, workflow_id: str, participants: List[str], 
                                 coordination_data: Dict) -> bool:
        """Coordinate a multi-agent workflow"""
        try:
            # Initialize workflow
            self.active_workflows[workflow_id] = {
                "participants": participants,
                "coordination_data": coordination_data,
                "status": "initializing",
                "started_at": datetime.now().isoformat(),
                "current_step": 0
            }
            
            # Create coordination lock
            self.coordination_locks[workflow_id] = threading.Lock()
            
            # Send coordination messages to participants
            for participant in participants:
                coordination_message = Message(
                    message_id=str(uuid.uuid4()),
                    from_agent="sync_engine",
                    to_agent=participant,
                    message_type=MessageType.COORDINATION,
                    content={
                        "workflow_id": workflow_id,
                        "action": "join_workflow",
                        "coordination_data": coordination_data
                    },
                    timestamp=datetime.now(),
                    priority=8,
                    requires_response=True
                )
                
                await self.send_message(coordination_message)
            
            self.active_workflows[workflow_id]["status"] = "coordinating"
            return True
            
        except Exception as e:
            print(f"Error coordinating workflow: {e}")
            return False
    
    def update_agent_state(self, agent_id: str, new_state: str):
        """Update agent state"""
        if agent_id in self.registered_agents:
            self.agent_states[agent_id] = new_state
            self.registered_agents[agent_id]["last_state_update"] = datetime.now().isoformat()
            
            # Broadcast state change
            self.broadcast_message(
                from_agent="sync_engine",
                message_type=MessageType.STATUS_UPDATE,
                content={
                    "event": "agent_state_changed",
                    "agent_id": agent_id,
                    "new_state": new_state
                }
            )
    
    async def message_processor(self):
        """Background task to process messages"""
        while True:
            try:
                # Process failed deliveries
                for agent_id, messages in self.message_queues.items():
                    if messages and agent_id in self.agent_connections:
                        # Try to deliver pending messages
                        for message in messages[:5]:  # Process up to 5 messages per cycle
                            try:
                                websocket = self.agent_connections[agent_id]
                                await websocket.send(json.dumps({
                                    "type": "pending_message",
                                    "message": asdict(message)
                                }, default=str))
                                
                                # Remove delivered message
                                self.message_queues[agent_id].remove(message)
                                
                            except Exception as e:
                                print(f"Message delivery failed for {agent_id}: {e}")
                                break
                
                await asyncio.sleep(1)  # Process every second
                
            except Exception as e:
                print(f"Message processor error: {e}")
                await asyncio.sleep(5)
    
    async def heartbeat_monitor(self):
        """Monitor agent heartbeats"""
        while True:
            try:
                current_time = datetime.now()
                
                for agent_id, agent_info in self.registered_agents.items():
                    last_heartbeat = datetime.fromisoformat(agent_info["last_heartbeat"])
                    time_diff = (current_time - last_heartbeat).total_seconds()
                    
                    if time_diff > 60:  # 1 minute timeout
                        # Mark agent as inactive
                        self.registered_agents[agent_id]["status"] = "inactive"
                        self.update_agent_state(agent_id, "disconnected")
                        
                        # Remove from connections
                        if agent_id in self.agent_connections:
                            del self.agent_connections[agent_id]
                    
                    elif time_diff > 30:  # 30 seconds warning
                        # Send heartbeat request
                        heartbeat_message = Message(
                            message_id=str(uuid.uuid4()),
                            from_agent="sync_engine",
                            to_agent=agent_id,
                            message_type=MessageType.HEARTBEAT,
                            content={"request": "heartbeat"},
                            timestamp=current_time,
                            priority=1
                        )
                        
                        await self.send_message(heartbeat_message)
                
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                print(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(30)
    
    async def cleanup_old_messages(self):
        """Clean up old messages and responses"""
        while True:
            try:
                current_time = datetime.now()
                
                # Clean up old pending responses (older than 1 hour)
                expired_responses = []
                for message_id, message in self.pending_responses.items():
                    time_diff = (current_time - message.timestamp).total_seconds()
                    if time_diff > 3600:  # 1 hour
                        expired_responses.append(message_id)
                
                for message_id in expired_responses:
                    del self.pending_responses[message_id]
                
                # Clean up old workflow data (older than 24 hours)
                expired_workflows = []
                for workflow_id, workflow in self.active_workflows.items():
                    started_at = datetime.fromisoformat(workflow["started_at"])
                    time_diff = (current_time - started_at).total_seconds()
                    if time_diff > 86400:  # 24 hours
                        expired_workflows.append(workflow_id)
                
                for workflow_id in expired_workflows:
                    del self.active_workflows[workflow_id]
                    if workflow_id in self.coordination_locks:
                        del self.coordination_locks[workflow_id]
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                print(f"Cleanup error: {e}")
                await asyncio.sleep(3600)
    
    def parse_websocket_message(self, data: Dict) -> Optional[Message]:
        """Parse WebSocket message data into Message object"""
        try:
            return Message(
                message_id=data.get("message_id", str(uuid.uuid4())),
                from_agent=data.get("from_agent"),
                to_agent=data.get("to_agent"),
                message_type=MessageType(data.get("message_type")),
                content=data.get("content"),
                timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                priority=data.get("priority", 5),
                requires_response=data.get("requires_response", False),
                correlation_id=data.get("correlation_id")
            )
        except Exception as e:
            print(f"Error parsing WebSocket message: {e}")
            return None
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get sync engine status"""
        uptime = time.time() - self.start_time
        
        return {
            "engine_id": self.engine_id,
            "status": self.status,
            "uptime_seconds": uptime,
            "registered_agents": len(self.registered_agents),
            "active_connections": len(self.agent_connections),
            "active_workflows": len(self.active_workflows),
            "message_stats": self.message_stats,
            "total_queued_messages": sum(len(queue) for queue in self.message_queues.values()),
            "pending_responses": len(self.pending_responses),
            "websocket_port": self.websocket_port
        }
    
    def get_agent_list(self) -> List[Dict]:
        """Get list of registered agents"""
        return [
            {
                "agent_id": agent_id,
                "status": info["status"],
                "state": self.agent_states.get(agent_id, "unknown"),
                "registered_at": info["registered_at"],
                "last_heartbeat": info["last_heartbeat"],
                "queued_messages": len(self.message_queues.get(agent_id, [])),
                "connected": agent_id in self.agent_connections
            }
            for agent_id, info in self.registered_agents.items()
        ]
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get workflow status"""
        return self.active_workflows.get(workflow_id)
    
    def subscribe_to_events(self, event_type: str, handler: Callable):
        """Subscribe to sync engine events"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
    
    def emit_event(self, event_type: str, event_data: Any):
        """Emit event to subscribers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(event_data)
                except Exception as e:
                    print(f"Event handler error: {e}")

# Global instance
sync_engine = SyncEngine()
