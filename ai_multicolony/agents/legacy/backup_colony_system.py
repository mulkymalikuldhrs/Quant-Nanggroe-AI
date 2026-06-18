"""
🔄 Backup Colony System - Distributed Backup and Redundancy Agent
Advanced AI agent for distributed backup management and system redundancy

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import logging
import hashlib
import shutil
import gzip
import time
import os
import sqlite3
import socket
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import requests
import subprocess
import tempfile
import zipfile
import tarfile
import base64

# Heavy dependency - made optional for graceful degradation
try:
    from cryptography.fernet import Fernet
    _CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    Fernet = None
    _CRYPTOGRAPHY_AVAILABLE = False

@dataclass
class BackupNode:
    """Backup node information"""
    node_id: str
    node_type: str  # local, remote, cloud, p2p
    location: str
    capacity_gb: float
    used_gb: float
    status: str  # active, inactive, syncing, error
    last_sync: Optional[datetime] = None
    encryption_key: Optional[str] = None
    connection_info: Dict[str, Any] = None

@dataclass
class BackupRecord:
    """Backup record information"""
    backup_id: str
    backup_type: str  # full, incremental, differential
    source_path: str
    backup_path: str
    file_count: int
    size_bytes: int
    created_at: datetime
    compression_ratio: float
    encryption_enabled: bool
    checksum: str
    nodes_stored: List[str]
    status: str = "completed"  # pending, in_progress, completed, failed

class BackupColonySystem:
    """
    Backup Colony System: Distributed backup management and redundancy
    
    Capabilities:
    - 🔄 Distributed backup management
    - 🌐 Multi-node synchronization
    - 🔒 Encrypted backup storage
    - 📦 Intelligent compression
    - 🔄 Real-time data replication
    - 🚨 Backup health monitoring
    - 🛡️ Redundancy management
    - 📊 Storage optimization
    - 🌍 Geographic distribution
    - 🔧 Automated recovery
    """
    
    def __init__(self):
        self.agent_id = "backup_colony_system"
        self.name = "Backup Colony System"
        self.status = "initializing"
        self.version = "1.0.0"
        self.start_time = datetime.now()
        
        # Core capabilities
        self.capabilities = [
            "distributed_backup",
            "multi_node_sync",
            "encrypted_storage",
            "intelligent_compression",
            "real_time_replication",
            "health_monitoring",
            "redundancy_management",
            "storage_optimization",
            "geographic_distribution",
            "automated_recovery"
        ]
        
        # Backup infrastructure
        self.backup_nodes = {}
        self.backup_records = {}
        self.sync_queue = []
        self.replication_factor = 3  # Minimum copies per backup
        
        # Backup configuration
        self.backup_config = {
            "auto_backup_interval": 3600,  # 1 hour
            "retention_policy": {
                "daily": 30,    # Keep 30 daily backups
                "weekly": 12,   # Keep 12 weekly backups
                "monthly": 12,  # Keep 12 monthly backups
                "yearly": 5     # Keep 5 yearly backups
            },
            "compression_level": 6,
            "encryption_enabled": True,
            "max_backup_size": 10 * 1024 * 1024 * 1024,  # 10GB
            "priority_paths": [
                "data/",
                "agents/",
                "core/",
                "config/",
                "projects/"
            ]
        }
        
        # Colony network settings
        self.colony_network = {
            "discovery_port": 8899,
            "sync_port": 8900,
            "heartbeat_interval": 30,
            "max_nodes": 10,
            "min_nodes": 2
        }
        
        # Encryption keys
        self.master_key = None
        self.node_keys = {}
        
        # Initialize logging
        self.setup_logging()
        
        # Initialize backup infrastructure
        self.initialize_backup_infrastructure()
        
        # Load existing configuration
        self.load_backup_configuration()
        
        self.logger.info("Backup Colony System initialized successfully")
        self.status = "ready"
    
    def setup_logging(self):
        """Setup logging for Backup Colony System"""
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "backup_colony.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("BackupColonySystem")
    
    def initialize_backup_infrastructure(self):
        """Initialize backup infrastructure and directories"""
        # Create backup directories
        backup_dirs = [
            "data/backups",
            "data/backups/local",
            "data/backups/remote", 
            "data/backups/incremental",
            "data/backups/metadata",
            "data/colony_nodes",
            "data/sync_cache"
        ]
        
        for directory in backup_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize local backup node
        self.initialize_local_node()
        
        # Initialize backup database
        self.initialize_backup_database()
        
        # Generate encryption keys
        self.initialize_encryption()
    
    def initialize_local_node(self):
        """Initialize local backup node"""
        local_node_id = f"local_{socket.gethostname()}"
        
        # Calculate available storage
        backup_path = Path("data/backups/local")
        disk_usage = shutil.disk_usage(backup_path)
        available_gb = disk_usage.free / (1024**3)
        
        local_node = BackupNode(
            node_id=local_node_id,
            node_type="local",
            location=socket.gethostname(),
            capacity_gb=available_gb,
            used_gb=0.0,
            status="active",
            last_sync=datetime.now(),
            connection_info={"path": str(backup_path)}
        )
        
        self.backup_nodes[local_node_id] = local_node
        self.logger.info(f"Local backup node initialized: {available_gb:.2f}GB available")
    
    def initialize_backup_database(self):
        """Initialize SQLite database for backup tracking"""
        db_dir = Path("data/backups")
        self.db_path = db_dir / "backup_records.db"
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backup_records (
                    backup_id TEXT PRIMARY KEY,
                    backup_type TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    backup_path TEXT NOT NULL,
                    file_count INTEGER,
                    size_bytes INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    compression_ratio REAL,
                    encryption_enabled BOOLEAN,
                    checksum TEXT,
                    nodes_stored TEXT,
                    status TEXT DEFAULT 'completed'
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backup_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    location TEXT,
                    capacity_gb REAL,
                    used_gb REAL,
                    status TEXT DEFAULT 'active',
                    last_sync TIMESTAMP,
                    connection_info TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_history (
                    sync_id TEXT PRIMARY KEY,
                    source_node TEXT,
                    target_node TEXT,
                    sync_type TEXT,
                    bytes_transferred INTEGER,
                    sync_time REAL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("Backup database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize backup database: {e}")
    
    def initialize_encryption(self):
        """Initialize encryption for secure backups"""
        try:
            if not _CRYPTOGRAPHY_AVAILABLE:
                self.logger.warning("cryptography package not installed - backup encryption disabled")
                self.master_key = None
                return
            
            # Generate or load master encryption key
            key_file = Path("data/backups/.master.key")
            
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    self.master_key = f.read()
            else:
                self.master_key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(self.master_key)
                # Make key file read-only
                os.chmod(key_file, 0o600)
            
            self.logger.info("Backup encryption initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption: {e}")
    
    def load_backup_configuration(self):
        """Load backup configuration from file"""
        config_file = Path("data/backups/colony_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.backup_config.update(config.get("backup_config", {}))
                    self.colony_network.update(config.get("colony_network", {}))
                    
                self.logger.info("Backup configuration loaded")
                
            except Exception as e:
                self.logger.error(f"Failed to load backup configuration: {e}")
    
    async def start_colony_network(self) -> Dict[str, Any]:
        """Start backup colony network"""
        self.logger.info("Starting backup colony network")
        
        try:
            # Start node discovery service
            asyncio.create_task(self._node_discovery_service())
            
            # Start synchronization service
            asyncio.create_task(self._synchronization_service())
            
            # Start health monitoring
            asyncio.create_task(self._health_monitoring_service())
            
            # Start automatic backup scheduler
            asyncio.create_task(self._backup_scheduler())
            
            self.logger.info("Backup colony network started successfully")
            return {
                "success": True,
                "local_node": list(self.backup_nodes.keys())[0],
                "discovery_port": self.colony_network["discovery_port"],
                "message": "Colony network is active and discovering nodes"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start colony network: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_backup(self, source_path: str, backup_type: str = "incremental", 
                          encrypt: bool = True) -> Dict[str, Any]:
        """Create a new backup"""
        self.logger.info(f"Creating {backup_type} backup of {source_path}")
        
        try:
            backup_id = hashlib.md5(f"{source_path}_{backup_type}_{datetime.now()}".encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{backup_id}_{timestamp}.tar.gz"
            
            # Determine backup path
            backup_dir = Path("data/backups/local")
            backup_path = backup_dir / backup_filename
            
            # Create compressed backup
            compression_start = time.time()
            original_size, compressed_size, file_count = await self._create_compressed_backup(
                source_path, backup_path, encrypt
            )
            compression_time = time.time() - compression_start
            
            # Calculate compression ratio
            compression_ratio = compressed_size / original_size if original_size > 0 else 0
            
            # Generate checksum
            checksum = await self._calculate_checksum(backup_path)
            
            # Create backup record
            backup_record = BackupRecord(
                backup_id=backup_id,
                backup_type=backup_type,
                source_path=source_path,
                backup_path=str(backup_path),
                file_count=file_count,
                size_bytes=compressed_size,
                created_at=datetime.now(),
                compression_ratio=compression_ratio,
                encryption_enabled=encrypt,
                checksum=checksum,
                nodes_stored=[list(self.backup_nodes.keys())[0]]  # Initially on local node
            )
            
            self.backup_records[backup_id] = backup_record
            
            # Save to database
            await self._save_backup_record(backup_record)
            
            # Queue for replication to other nodes
            await self._queue_for_replication(backup_id)
            
            self.logger.info(f"Backup created: {backup_id} ({compressed_size/1024/1024:.2f}MB, "
                           f"{compression_ratio:.2f} compression ratio)")
            
            return {
                "success": True,
                "backup_id": backup_id,
                "size_mb": compressed_size / 1024 / 1024,
                "compression_ratio": compression_ratio,
                "file_count": file_count,
                "creation_time": compression_time,
                "encrypted": encrypt
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return {"success": False, "error": str(e)}
    
    async def _create_compressed_backup(self, source_path: str, backup_path: Path, 
                                      encrypt: bool) -> tuple:
        """Create compressed and optionally encrypted backup"""
        original_size = 0
        file_count = 0
        
        # Create temporary tar file
        with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as temp_tar:
            temp_tar_path = temp_tar.name
        
        try:
            # Create tar archive
            with tarfile.open(temp_tar_path, 'w') as tar:
                source = Path(source_path)
                if source.is_file():
                    tar.add(source, arcname=source.name)
                    original_size = source.stat().st_size
                    file_count = 1
                else:
                    for item in source.rglob('*'):
                        if item.is_file():
                            tar.add(item, arcname=item.relative_to(source.parent))
                            original_size += item.stat().st_size
                            file_count += 1
            
            # Compress and optionally encrypt
            with open(temp_tar_path, 'rb') as tar_file:
                tar_data = tar_file.read()
            
            if encrypt and self.master_key:
                fernet = Fernet(self.master_key)
                tar_data = fernet.encrypt(tar_data)
            
            # Compress
            with gzip.open(backup_path, 'wb', compresslevel=self.backup_config["compression_level"]) as gz_file:
                gz_file.write(tar_data)
            
            compressed_size = backup_path.stat().st_size
            
            return original_size, compressed_size, file_count
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_tar_path):
                os.unlink(temp_tar_path)
    
    async def restore_backup(self, backup_id: str, restore_path: str) -> Dict[str, Any]:
        """Restore a backup to specified location"""
        self.logger.info(f"Restoring backup {backup_id} to {restore_path}")
        
        if backup_id not in self.backup_records:
            return {"success": False, "error": "Backup not found"}
        
        backup_record = self.backup_records[backup_id]
        
        try:
            # Find backup file on available nodes
            backup_file = None
            for node_id in backup_record.nodes_stored:
                if node_id in self.backup_nodes:
                    node = self.backup_nodes[node_id]
                    if node.node_type == "local":
                        potential_path = Path(backup_record.backup_path)
                        if potential_path.exists():
                            backup_file = potential_path
                            break
            
            if not backup_file:
                return {"success": False, "error": "Backup file not accessible"}
            
            # Verify checksum
            current_checksum = await self._calculate_checksum(backup_file)
            if current_checksum != backup_record.checksum:
                return {"success": False, "error": "Backup integrity check failed"}
            
            # Restore backup
            restore_start = time.time()
            
            # Decompress
            with gzip.open(backup_file, 'rb') as gz_file:
                compressed_data = gz_file.read()
            
            # Decrypt if encrypted
            if backup_record.encryption_enabled and self.master_key:
                fernet = Fernet(self.master_key)
                compressed_data = fernet.decrypt(compressed_data)
            
            # Extract tar archive
            with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as temp_tar:
                temp_tar.write(compressed_data)
                temp_tar_path = temp_tar.name
            
            try:
                with tarfile.open(temp_tar_path, 'r') as tar:
                    tar.extractall(path=restore_path)
                
                restore_time = time.time() - restore_start
                
                self.logger.info(f"Backup {backup_id} restored successfully in {restore_time:.2f}s")
                
                return {
                    "success": True,
                    "backup_id": backup_id,
                    "restore_path": restore_path,
                    "file_count": backup_record.file_count,
                    "restore_time": restore_time
                }
                
            finally:
                if os.path.exists(temp_tar_path):
                    os.unlink(temp_tar_path)
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup {backup_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def discover_colony_nodes(self) -> Dict[str, Any]:
        """Discover other backup colony nodes on the network"""
        self.logger.info("Discovering backup colony nodes")
        
        discovered_nodes = []
        
        try:
            # Broadcast discovery message
            discovery_message = {
                "type": "node_discovery",
                "node_id": list(self.backup_nodes.keys())[0],
                "capabilities": self.capabilities,
                "timestamp": datetime.now().isoformat()
            }
            
            # Simple local network discovery (can be extended)
            for i in range(1, 255):
                try:
                    target_ip = f"192.168.1.{i}"
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    
                    result = sock.connect_ex((target_ip, self.colony_network["discovery_port"]))
                    if result == 0:
                        # Found potential node
                        discovered_nodes.append({
                            "ip": target_ip,
                            "port": self.colony_network["discovery_port"],
                            "discovered_at": datetime.now().isoformat()
                        })
                    
                    sock.close()
                    
                except Exception:
                    pass  # Ignore errors for individual IPs
            
            self.logger.info(f"Discovered {len(discovered_nodes)} potential colony nodes")
            return {
                "success": True,
                "discovered_nodes": discovered_nodes,
                "discovery_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Node discovery failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_colony_status(self) -> Dict[str, Any]:
        """Get comprehensive backup colony status"""
        # Calculate storage statistics
        total_capacity = sum(node.capacity_gb for node in self.backup_nodes.values())
        total_used = sum(node.used_gb for node in self.backup_nodes.values())
        
        # Calculate backup statistics
        total_backups = len(self.backup_records)
        recent_backups = len([
            b for b in self.backup_records.values()
            if (datetime.now() - b.created_at).total_seconds() < 86400
        ])
        
        # Calculate redundancy statistics
        replicated_backups = len([
            b for b in self.backup_records.values()
            if len(b.nodes_stored) >= self.replication_factor
        ])
        
        return {
            "agent_status": self.status,
            "colony_nodes": len(self.backup_nodes),
            "active_nodes": len([n for n in self.backup_nodes.values() if n.status == "active"]),
            "storage": {
                "total_capacity_gb": round(total_capacity, 2),
                "total_used_gb": round(total_used, 2),
                "usage_percentage": round((total_used / total_capacity * 100) if total_capacity > 0 else 0, 2)
            },
            "backups": {
                "total_backups": total_backups,
                "recent_backups_24h": recent_backups,
                "replicated_backups": replicated_backups,
                "replication_factor": self.replication_factor
            },
            "sync_queue": len(self.sync_queue),
            "last_backup": max([b.created_at for b in self.backup_records.values()]).isoformat() if self.backup_records else None,
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600
        }
    
    async def _node_discovery_service(self):
        """Background service for node discovery"""
        while True:
            try:
                await self.discover_colony_nodes()
                await asyncio.sleep(300)  # Discover every 5 minutes
            except Exception as e:
                self.logger.error(f"Node discovery service error: {e}")
                await asyncio.sleep(60)
    
    async def _synchronization_service(self):
        """Background service for data synchronization"""
        while True:
            try:
                if self.sync_queue:
                    backup_id = self.sync_queue.pop(0)
                    await self._replicate_backup(backup_id)
                
                await asyncio.sleep(30)  # Check sync queue every 30 seconds
            except Exception as e:
                self.logger.error(f"Synchronization service error: {e}")
                await asyncio.sleep(60)
    
    async def _health_monitoring_service(self):
        """Background service for monitoring colony health"""
        while True:
            try:
                # Check node health
                for node_id, node in self.backup_nodes.items():
                    if node.node_type == "local":
                        # Update local node storage info
                        backup_path = Path(node.connection_info["path"])
                        if backup_path.exists():
                            disk_usage = shutil.disk_usage(backup_path)
                            node.capacity_gb = disk_usage.total / (1024**3)
                            node.used_gb = (disk_usage.total - disk_usage.free) / (1024**3)
                            node.last_sync = datetime.now()
                            node.status = "active"
                        else:
                            node.status = "error"
                
                await asyncio.sleep(self.colony_network["heartbeat_interval"])
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _backup_scheduler(self):
        """Background service for automatic backups"""
        while True:
            try:
                # Check if it's time for automatic backup
                last_backup_time = None
                if self.backup_records:
                    last_backup_time = max(b.created_at for b in self.backup_records.values())
                
                time_since_last = float('inf')
                if last_backup_time:
                    time_since_last = (datetime.now() - last_backup_time).total_seconds()
                
                if time_since_last >= self.backup_config["auto_backup_interval"]:
                    # Create automatic backup of priority paths
                    for priority_path in self.backup_config["priority_paths"]:
                        if Path(priority_path).exists():
                            await self.create_backup(priority_path, "incremental", True)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Backup scheduler error: {e}")
                await asyncio.sleep(600)
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        import hashlib
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def _save_backup_record(self, backup_record: BackupRecord):
        """Save backup record to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO backup_records 
                (backup_id, backup_type, source_path, backup_path, file_count, 
                 size_bytes, compression_ratio, encryption_enabled, checksum, 
                 nodes_stored, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                backup_record.backup_id,
                backup_record.backup_type,
                backup_record.source_path,
                backup_record.backup_path,
                backup_record.file_count,
                backup_record.size_bytes,
                backup_record.compression_ratio,
                backup_record.encryption_enabled,
                backup_record.checksum,
                json.dumps(backup_record.nodes_stored),
                backup_record.status
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to save backup record: {e}")
    
    async def _queue_for_replication(self, backup_id: str):
        """Queue backup for replication to other nodes"""
        if backup_id not in self.sync_queue:
            self.sync_queue.append(backup_id)
    
    async def _replicate_backup(self, backup_id: str):
        """Replicate backup to other available nodes"""
        # Implementation would depend on available remote nodes
        # For now, just log the replication attempt
        self.logger.info(f"Replication queued for backup {backup_id}")

# Global instance
backup_colony_system = BackupColonySystem()

# Export for use by other modules
__all__ = ['BackupColonySystem', 'backup_colony_system', 'BackupNode', 'BackupRecord']
