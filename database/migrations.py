"""
🔄 Database Migrations - Schema Version Management
Handles database schema updates and migrations

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///data/agentic.db')
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
        
        # Ensure migration tracking table exists
        self._create_migration_table()
    
    def _create_migration_table(self):
        """Create migration tracking table if it doesn't exist"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version VARCHAR(50) UNIQUE NOT NULL,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
    
    def create_migration(self, name: str, description: str = "") -> str:
        """Create a new migration file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = f"{timestamp}_{name}"
        filename = f"{version}.py"
        filepath = self.migrations_dir / filename
        
        template = f'''"""
Migration: {version}
Description: {description}
Created: {datetime.now().isoformat()}
"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

def up(connection):
    """Apply migration"""
    # Add your migration code here
    # Example:
    # connection.execute(text("ALTER TABLE agents ADD COLUMN new_field VARCHAR(100)"))
    logger.debug("Migration up: no-op")

def down(connection):
    """Rollback migration""" 
    # Add rollback code here
    # Example:
    # connection.execute(text("ALTER TABLE agents DROP COLUMN new_field"))
    logger.debug("Migration down: no-op")
'''
        
        with open(filepath, 'w') as f:
            f.write(template)
        
        print(f"✅ Created migration: {filename}")
        return version
    
    def get_pending_migrations(self) -> list:
        """Get list of pending migrations"""
        # Get applied migrations
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM schema_migrations ORDER BY version"))
            applied = {row[0] for row in result}
        
        # Get all migration files
        migration_files = sorted([f.stem for f in self.migrations_dir.glob("*.py") if not f.name.startswith("__")])
        
        # Return pending migrations
        return [m for m in migration_files if m not in applied]
    
    def run_migrations(self) -> bool:
        """Run all pending migrations"""
        try:
            pending = self.get_pending_migrations()
            
            if not pending:
                print("✅ No pending migrations")
                return True
            
            print(f"🔄 Running {len(pending)} pending migrations...")
            
            for version in pending:
                self._apply_migration(version)
            
            print("✅ All migrations completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False
    
    def _apply_migration(self, version: str):
        """Apply a single migration"""
        migration_file = self.migrations_dir / f"{version}.py"
        
        if not migration_file.exists():
            raise FileNotFoundError(f"Migration file not found: {migration_file}")
        
        # Load migration module
        spec = __import__(f"database.migrations.{version}", fromlist=['up', 'down'])
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Apply migration
                spec.up(conn)
                
                # Record migration as applied
                conn.execute(text("""
                    INSERT INTO schema_migrations (version, description) 
                    VALUES (:version, :description)
                """), {
                    "version": version,
                    "description": getattr(spec, '__doc__', '').strip()
                })
                
                trans.commit()
                print(f"   ✅ Applied migration: {version}")
                
            except Exception as e:
                trans.rollback()
                raise Exception(f"Failed to apply migration {version}: {e}")
    
    def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration"""
        try:
            migration_file = self.migrations_dir / f"{version}.py"
            
            if not migration_file.exists():
                raise FileNotFoundError(f"Migration file not found: {migration_file}")
            
            # Load migration module
            spec = __import__(f"database.migrations.{version}", fromlist=['up', 'down'])
            
            with self.engine.connect() as conn:
                trans = conn.begin()
                try:
                    # Rollback migration
                    spec.down(conn)
                    
                    # Remove migration record
                    conn.execute(text("DELETE FROM schema_migrations WHERE version = :version"), {"version": version})
                    
                    trans.commit()
                    print(f"✅ Rolled back migration: {version}")
                    return True
                    
                except Exception as e:
                    trans.rollback()
                    raise Exception(f"Failed to rollback migration {version}: {e}")
                    
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False
    
    def get_migration_status(self) -> dict:
        """Get current migration status"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT version, description, applied_at 
                FROM schema_migrations 
                ORDER BY applied_at DESC 
                LIMIT 10
            """))
            applied = [{"version": row[0], "description": row[1], "applied_at": row[2]} for row in result]
        
        pending = self.get_pending_migrations()
        
        return {
            "applied_count": len(applied),
            "pending_count": len(pending),
            "latest_applied": applied[0] if applied else None,
            "pending_migrations": pending[:5],  # Show first 5 pending
            "recent_applied": applied[:5]  # Show last 5 applied
        }

# Initial migration files
INITIAL_MIGRATIONS = {
    "20240101_000001_initial_schema": '''"""
Initial schema migration
Creates all core tables for the Agentic AI System
"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

def up(connection):
    """Apply initial schema"""
    # This migration is handled by the initial database setup
    # All tables are created by SQLAlchemy models
    logger.debug("Migration 000001 (initial_schema): no-op, tables created by SQLAlchemy models")

def down(connection):
    """Rollback initial schema"""
    # Drop all tables (use with extreme caution)
    tables = [
        'api_logs', 'user_sessions', 'knowledge_entries', 'system_metrics',
        'deployments', 'workflow_steps', 'workflow_executions', 'workflows',
        'memories', 'tasks', 'agents'
    ]
    
    for table in tables:
        try:
            connection.execute(text(f"DROP TABLE IF EXISTS {table}"))
        except Exception:
            pass
''',
    
    "20240101_000002_add_agent_performance_tracking": '''"""
Add performance tracking fields to agents
Adds metrics and monitoring capabilities
"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

def up(connection):
    """Add performance tracking"""
    try:
        connection.execute(text("""
            ALTER TABLE agents ADD COLUMN total_tasks INTEGER DEFAULT 0
        """))
    except Exception:
        pass
        
    try:
        connection.execute(text("""
            ALTER TABLE agents ADD COLUMN successful_tasks INTEGER DEFAULT 0
        """))
    except Exception:
        pass
        
    try:
        connection.execute(text("""
            ALTER TABLE agents ADD COLUMN avg_response_time FLOAT DEFAULT 0.0
        """))
    except Exception:
        pass

def down(connection):
    """Remove performance tracking"""
    try:
        connection.execute(text("ALTER TABLE agents DROP COLUMN total_tasks"))
        connection.execute(text("ALTER TABLE agents DROP COLUMN successful_tasks"))
        connection.execute(text("ALTER TABLE agents DROP COLUMN avg_response_time"))
    except Exception:
        pass
''',
    
    "20240101_000003_add_workflow_templates": '''"""
Add workflow template support
Enables reusable workflow definitions
"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

def up(connection):
    """Add workflow template support"""
    try:
        connection.execute(text("""
            ALTER TABLE workflows ADD COLUMN is_template BOOLEAN DEFAULT FALSE
        """))
    except Exception:
        pass
        
    try:
        connection.execute(text("""
            ALTER TABLE workflows ADD COLUMN template_version VARCHAR(20) DEFAULT '1.0'
        """))
    except Exception:
        pass

def down(connection):
    """Remove workflow template support"""
    try:
        connection.execute(text("ALTER TABLE workflows DROP COLUMN is_template"))
        connection.execute(text("ALTER TABLE workflows DROP COLUMN template_version"))
    except Exception:
        pass
'''
}

def create_initial_migrations():
    """Create initial migration files if they don't exist"""
    migrations_dir = Path(__file__).parent / "migrations"
    migrations_dir.mkdir(exist_ok=True)
    
    for filename, content in INITIAL_MIGRATIONS.items():
        filepath = migrations_dir / f"{filename}.py"
        if not filepath.exists():
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"✅ Created initial migration: {filename}.py")

def run_migrations(database_url: str = None) -> bool:
    """Run all pending migrations"""
    # Create initial migrations
    create_initial_migrations()
    
    # Run migrations
    manager = MigrationManager(database_url)
    return manager.run_migrations()

def create_migration(name: str, description: str = "") -> str:
    """Create a new migration"""
    manager = MigrationManager()
    return manager.create_migration(name, description)

def get_migration_status(database_url: str = None) -> dict:
    """Get migration status"""
    manager = MigrationManager(database_url)
    return manager.get_migration_status()

if __name__ == "__main__":
    # Run migrations when executed directly
    run_migrations()
