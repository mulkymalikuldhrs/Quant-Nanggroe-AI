"""
🏗️ Database Initialization - Setup and Configuration
Initializes database schema and seed data

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
import asyncio
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import (
    Base, Agent, Task, Memory, Workflow, WorkflowExecution, 
    Deployment, SystemMetric, KnowledgeEntry, UserSession, APILog
)

def initialize_database(database_url: str = None) -> bool:
    """
    Initialize the database with schema and seed data
    
    Args:
        database_url: Database connection URL
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get database URL
        db_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///data/agentic.db')
        
        # Create data directory if using SQLite
        if db_url.startswith('sqlite:'):
            db_path = db_url.replace('sqlite:///', '')
            data_dir = Path(db_path).parent
            data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create engine
        engine = create_engine(db_url, echo=False)
        
        # Create all tables
        print("🏗️ Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        # Create session
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Seed initial data
            print("🌱 Seeding initial data...")
            _seed_agents(session)
            _seed_workflows(session)
            _seed_knowledge_base(session)
            
            # Commit changes
            session.commit()
            print("✅ Database initialization completed successfully!")
            return True
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error seeding data: {e}")
            return False
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def _seed_agents(session):
    """Seed initial agent data"""
    
    # Check if agents already exist
    if session.query(Agent).count() > 0:
        print("   ⏭️ Agents already exist, skipping...")
        return
    
    # Core system agents
    core_agents = [
        {
            "agent_id": "prompt_master",
            "name": "Prompt Master Agent",
            "status": "ready",
            "capabilities": [
                "central_coordination", "task_routing", "workflow_management",
                "agent_communication", "system_orchestration"
            ],
            "config": {
                "priority": 1,
                "max_concurrent_tasks": 10,
                "auto_start": True
            }
        },
        {
            "agent_id": "cybershell",
            "name": "CyberShell Agent",
            "status": "ready",
            "capabilities": [
                "shell_execution", "script_running", "system_commands",
                "file_operations", "process_management"
            ],
            "config": {
                "allowed_commands": ["ls", "cat", "grep", "find", "git"],
                "timeout": 300,
                "max_concurrent": 3
            }
        },
        {
            "agent_id": "agent_maker",
            "name": "Agent Maker",
            "status": "ready",
            "capabilities": [
                "agent_creation", "dynamic_spawning", "template_generation",
                "capability_assignment", "lifecycle_management"
            ],
            "config": {
                "max_agents": 50,
                "templates": ["data_scientist", "developer", "writer"]
            }
        },
        {
            "agent_id": "ui_designer",
            "name": "UI Designer Agent",
            "status": "ready",
            "capabilities": [
                "ui_generation", "component_creation", "react_development",
                "tailwind_styling", "responsive_design"
            ],
            "config": {
                "frameworks": ["react", "vue", "angular"],
                "css_framework": "tailwind"
            }
        },
        {
            "agent_id": "dev_engine",
            "name": "Dev Engine Agent",
            "status": "ready",
            "capabilities": [
                "project_scaffolding", "code_generation", "build_automation",
                "dependency_management", "development_tools"
            ],
            "config": {
                "supported_languages": ["python", "javascript", "typescript"],
                "frameworks": ["fastapi", "express", "nextjs"]
            }
        },
        {
            "agent_id": "data_sync",
            "name": "Data Sync Agent", 
            "status": "ready",
            "capabilities": [
                "database_sync", "data_migration", "backup_management",
                "replication", "consistency_check"
            ],
            "config": {
                "databases": ["sqlite", "postgresql", "redis"],
                "sync_interval": 300
            }
        },
        {
            "agent_id": "fullstack_dev",
            "name": "Full Stack Developer Agent",
            "status": "ready",
            "capabilities": [
                "full_app_development", "api_creation", "frontend_backend",
                "database_design", "deployment_ready"
            ],
            "config": {
                "tech_stack": ["react", "fastapi", "postgresql"],
                "deployment_targets": ["netlify", "vercel", "railway"]
            }
        },
        {
            "agent_id": "deploy_manager",
            "name": "Deploy Manager Agent",
            "status": "ready",
            "capabilities": [
                "multi_platform_deployment", "infrastructure_management",
                "cicd_automation", "environment_config", "health_monitoring"
            ],
            "config": {
                "platforms": ["netlify", "vercel", "railway", "docker"],
                "auto_deploy": True
            }
        },
        {
            "agent_id": "prompt_generator",
            "name": "Prompt Generator Agent",
            "status": "ready",
            "capabilities": [
                "prompt_creation", "prompt_optimization", "role_based_prompts",
                "task_specific_prompts", "template_generation"
            ],
            "config": {
                "patterns": ["role_task", "chain_of_thought", "few_shot"],
                "optimization": True
            }
        }
    ]
    
    # Create agent records
    for agent_data in core_agents:
        agent = Agent(**agent_data)
        session.add(agent)
    
    print(f"   ✅ Seeded {len(core_agents)} core agents")

def _seed_workflows(session):
    """Seed initial workflow templates"""
    
    # Check if workflows already exist
    if session.query(Workflow).count() > 0:
        print("   ⏭️ Workflows already exist, skipping...")
        return
    
    # Standard workflows
    workflows = [
        {
            "workflow_id": "standard_development",
            "name": "Standard Development Workflow",
            "description": "Complete application development from planning to deployment",
            "definition": {
                "steps": [
                    {
                        "id": "planning",
                        "agent": "prompt_master",
                        "action": "analyze_requirements",
                        "timeout": 300
                    },
                    {
                        "id": "scaffolding",
                        "agent": "dev_engine", 
                        "action": "create_project_structure",
                        "depends_on": ["planning"]
                    },
                    {
                        "id": "ui_design",
                        "agent": "ui_designer",
                        "action": "create_components",
                        "depends_on": ["scaffolding"]
                    },
                    {
                        "id": "backend_development",
                        "agent": "fullstack_dev",
                        "action": "create_api",
                        "depends_on": ["scaffolding"]
                    },
                    {
                        "id": "integration",
                        "agent": "fullstack_dev",
                        "action": "integrate_frontend_backend",
                        "depends_on": ["ui_design", "backend_development"]
                    },
                    {
                        "id": "deployment",
                        "agent": "deploy_manager",
                        "action": "deploy_application",
                        "depends_on": ["integration"]
                    }
                ]
            },
            "status": "active"
        },
        {
            "workflow_id": "quick_prototype",
            "name": "Quick Prototype Workflow",
            "description": "Rapid prototyping for concept validation",
            "definition": {
                "steps": [
                    {
                        "id": "concept_analysis",
                        "agent": "prompt_master",
                        "action": "analyze_concept"
                    },
                    {
                        "id": "ui_mockup",
                        "agent": "ui_designer",
                        "action": "create_mockup",
                        "depends_on": ["concept_analysis"]
                    },
                    {
                        "id": "prototype_build",
                        "agent": "dev_engine",
                        "action": "build_prototype",
                        "depends_on": ["ui_mockup"]
                    },
                    {
                        "id": "quick_deploy",
                        "agent": "deploy_manager",
                        "action": "deploy_prototype",
                        "depends_on": ["prototype_build"]
                    }
                ]
            },
            "status": "active"
        },
        {
            "workflow_id": "agent_creation",
            "name": "Dynamic Agent Creation Workflow",
            "description": "Create new specialized agents on demand",
            "definition": {
                "steps": [
                    {
                        "id": "requirement_analysis",
                        "agent": "prompt_master",
                        "action": "analyze_agent_requirements"
                    },
                    {
                        "id": "prompt_generation",
                        "agent": "prompt_generator",
                        "action": "create_agent_prompt",
                        "depends_on": ["requirement_analysis"]
                    },
                    {
                        "id": "agent_instantiation",
                        "agent": "agent_maker",
                        "action": "create_agent",
                        "depends_on": ["prompt_generation"]
                    },
                    {
                        "id": "agent_testing",
                        "agent": "prompt_master",
                        "action": "test_new_agent",
                        "depends_on": ["agent_instantiation"]
                    }
                ]
            },
            "status": "active"
        }
    ]
    
    # Create workflow records
    for workflow_data in workflows:
        workflow = Workflow(**workflow_data)
        session.add(workflow)
    
    print(f"   ✅ Seeded {len(workflows)} workflow templates")

def _seed_knowledge_base(session):
    """Seed initial knowledge base entries"""
    
    # Check if knowledge entries already exist
    if session.query(KnowledgeEntry).count() > 0:
        print("   ⏭️ Knowledge base already exists, skipping...")
        return
    
    # Knowledge base entries
    knowledge_entries = [
        {
            "entry_id": "kb_001",
            "title": "Agentic AI System Architecture",
            "content": """The Agentic AI System is a multi-agent platform with the following components:
            
Core Agents:
- Prompt Master: Central coordination and task routing
- CyberShell: Shell and command execution
- Agent Maker: Dynamic agent creation
- UI Designer: User interface generation
- Dev Engine: Project scaffolding and development
- Data Sync: Database synchronization
- Full Stack Dev: Complete application development
- Deploy Manager: Multi-platform deployment
- Prompt Generator: AI prompt optimization

The system uses a hub-and-spoke architecture with the Prompt Master as the central coordinator.""",
            "category": "system_architecture",
            "tags": ["architecture", "agents", "core_system"],
            "source": "system_documentation"
        },
        {
            "entry_id": "kb_002",
            "title": "Supported Deployment Platforms",
            "content": """The Deploy Manager supports deployment to multiple platforms:

Static Hosting:
- Netlify: Static sites and JAMstack applications
- Vercel: Frontend applications with serverless functions

Container Hosting:
- Railway: Full-stack applications with databases
- Heroku: Traditional PaaS deployment

Cloud Platforms:
- AWS: Lambda, EC2, S3, CloudFront
- Google Cloud: Cloud Run, App Engine
- Docker: Local containerization

Each platform has specific configuration requirements and capabilities.""",
            "category": "deployment",
            "tags": ["deployment", "platforms", "hosting"],
            "source": "deployment_guide"
        },
        {
            "entry_id": "kb_003",
            "title": "Agent Communication Protocol",
            "content": """Agents communicate using a structured message format:

{
    "from_agent": "sender_agent_id",
    "to_agent": "recipient_agent_id", 
    "message_type": "task|response|notification",
    "task_id": "unique_task_identifier",
    "content": {
        "action": "specific_action_to_perform",
        "data": "relevant_data_payload",
        "context": "additional_context"
    },
    "timestamp": "ISO_8601_timestamp",
    "priority": "low|medium|high|urgent"
}

Messages are routed through the Sync Engine for coordination.""",
            "category": "communication",
            "tags": ["communication", "protocol", "messages"],
            "source": "technical_specification"
        },
        {
            "entry_id": "kb_004",
            "title": "Best Practices for Agent Development",
            "content": """When creating new agents, follow these best practices:

1. Single Responsibility: Each agent should have a clear, focused purpose
2. Idempotency: Operations should be safe to retry
3. Error Handling: Implement comprehensive error handling and recovery
4. Logging: Provide detailed logging for debugging and monitoring
5. Configuration: Use configuration for customizable behavior
6. Testing: Include unit tests and integration tests
7. Documentation: Document capabilities and usage patterns
8. Performance: Consider resource usage and optimization
9. Security: Implement appropriate security measures
10. Compatibility: Ensure compatibility with existing agents""",
            "category": "development",
            "tags": ["best_practices", "development", "guidelines"],
            "source": "development_guide"
        },
        {
            "entry_id": "kb_005",
            "title": "Indonesian AI Development Ecosystem",
            "content": """Indonesia has a growing AI development ecosystem with several key initiatives:

Government Initiatives:
- National AI Strategy 2020-2045
- Digital Transformation programs
- AI research funding

Educational Institutions:
- University of Indonesia (UI)
- Institut Teknologi Bandung (ITB)
- Universitas Gadjah Mada (UGM)

Industry Players:
- Gojek: Southeast Asia's leading super-app
- Tokopedia: Major e-commerce platform
- Local AI startups and research labs

The Agentic AI System is designed to contribute to this ecosystem by providing accessible AI automation tools.""",
            "category": "indonesia_ai",
            "tags": ["indonesia", "ai_ecosystem", "technology"],
            "source": "industry_research"
        }
    ]
    
    # Create knowledge entries
    for entry_data in knowledge_entries:
        entry = KnowledgeEntry(**entry_data)
        session.add(entry)
    
    print(f"   ✅ Seeded {len(knowledge_entries)} knowledge base entries")

def reset_database(database_url: str = None):
    """
    Reset the database by dropping and recreating all tables
    WARNING: This will delete all data!
    """
    try:
        db_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///data/agentic.db')
        engine = create_engine(db_url, echo=False)
        
        print("⚠️ Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        
        print("🏗️ Recreating tables...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database reset completed!")
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

if __name__ == "__main__":
    # Initialize database when run directly
    initialize_database()
