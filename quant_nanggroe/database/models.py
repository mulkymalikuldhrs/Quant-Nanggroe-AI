"""
📊 Database Models - SQLAlchemy ORM Models
Defines database schema for the Agentic AI System

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

class Agent(Base):
    """Agent model for storing agent information"""
    __tablename__ = 'agents'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    status = Column(String(50), default='ready')
    capabilities = Column(JSON, default=list)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tasks = relationship("Task", back_populates="agent")
    memories = relationship("Memory", back_populates="agent")

class Task(Base):
    """Task model for storing task information"""
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(100), unique=True, nullable=False)
    agent_id = Column(String(100), ForeignKey('agents.agent_id'), nullable=False)
    status = Column(String(50), default='pending')
    priority = Column(String(20), default='medium')
    request = Column(Text, nullable=False)
    context = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")

class Memory(Base):
    """Memory model for storing agent memories and experiences"""
    __tablename__ = 'memories'
    
    id = Column(Integer, primary_key=True)
    memory_id = Column(String(100), unique=True, nullable=False)
    agent_id = Column(String(100), ForeignKey('agents.agent_id'), nullable=False)
    type = Column(String(50), nullable=False)  # task, interaction, learning, etc.
    content = Column(JSON, nullable=False)
    extra_data = Column(JSON, default=dict)
    importance = Column(Float, default=0.5)
    accessed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_accessed = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    agent = relationship("Agent", back_populates="memories")

class Workflow(Base):
    """Workflow model for storing workflow definitions and executions"""
    __tablename__ = 'workflows'
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    definition = Column(JSON, nullable=False)
    status = Column(String(50), default='draft')
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    executions = relationship("WorkflowExecution", back_populates="workflow")

class WorkflowExecution(Base):
    """Workflow execution model for tracking workflow runs"""
    __tablename__ = 'workflow_executions'
    
    id = Column(Integer, primary_key=True)
    execution_id = Column(String(100), unique=True, nullable=False)
    workflow_id = Column(String(100), ForeignKey('workflows.workflow_id'), nullable=False)
    status = Column(String(50), default='running')
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    steps = relationship("WorkflowStep", back_populates="execution")

class WorkflowStep(Base):
    """Workflow step model for tracking individual step executions"""
    __tablename__ = 'workflow_steps'
    
    id = Column(Integer, primary_key=True)
    step_id = Column(String(100), nullable=False)
    execution_id = Column(String(100), ForeignKey('workflow_executions.execution_id'), nullable=False)
    agent_id = Column(String(100), nullable=False)
    step_number = Column(Integer, nullable=False)
    status = Column(String(50), default='pending')
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    execution = relationship("WorkflowExecution", back_populates="steps")

class Deployment(Base):
    """Deployment model for tracking application deployments"""
    __tablename__ = 'deployments'
    
    id = Column(Integer, primary_key=True)
    deployment_id = Column(String(100), unique=True, nullable=False)
    platform = Column(String(50), nullable=False)
    app_name = Column(String(200), nullable=False)
    environment = Column(String(50), default='production')
    status = Column(String(50), default='deploying')
    url = Column(String(500), nullable=True)
    config = Column(JSON, default=dict)
    logs = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

class SystemMetric(Base):
    """System metrics model for monitoring and analytics"""
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True)
    metric_type = Column(String(50), nullable=False)  # cpu, memory, response_time, etc.
    component = Column(String(100), nullable=False)   # agent_id or system component
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)
    extra_data = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class KnowledgeEntry(Base):
    """Knowledge base entries for RAG and context injection"""
    __tablename__ = 'knowledge_entries'
    
    id = Column(Integer, primary_key=True)
    entry_id = Column(String(100), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    tags = Column(JSON, default=list)
    embedding = Column(JSON, nullable=True)  # Vector embedding for semantic search
    source = Column(String(500), nullable=True)
    relevance_score = Column(Float, default=0.0)
    access_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class UserSession(Base):
    """User session model for web interface"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)
    user_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_activity = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)

class APILog(Base):
    """API request log model"""
    __tablename__ = 'api_logs'
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(100), unique=True, nullable=False)
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time = Column(Float, nullable=False)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    request_data = Column(JSON, default=dict)
    response_data = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/agentic.db')

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    """Get database session"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """Drop all tables (use with caution)"""
    Base.metadata.drop_all(bind=engine)
