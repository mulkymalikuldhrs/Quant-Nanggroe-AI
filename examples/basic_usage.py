"""
🚀 Basic Usage Examples - Agentic AI System
Simple examples showing how to use the multi-agent system

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.prompt_master import prompt_master
from agents.cybershell import cybershell_agent
from agents.agent_maker import agent_maker
from agents.ui_designer import ui_designer_agent
from agents.dev_engine import dev_engine_agent
from agents.fullstack_dev import fullstack_dev_agent
from agents.deploy_manager import deploy_manager_agent

async def example_1_basic_shell_commands():
    """Example 1: Execute basic shell commands"""
    print("🖥️ Example 1: Basic Shell Commands")
    print("-" * 50)
    
    # Execute simple command
    result = await cybershell_agent.process_task({
        "action": "execute_command",
        "command": "echo 'Hello from Agentic AI System!'"
    })
    
    print(f"Command output: {result.get('output', 'No output')}")
    
    # List files in current directory
    result = await cybershell_agent.process_task({
        "action": "list_files",
        "path": "."
    })
    
    print(f"Files found: {len(result.get('files', []))}")
    print()

async def example_2_create_react_component():
    """Example 2: Create a React component"""
    print("🎨 Example 2: Create React Component")
    print("-" * 50)
    
    result = await ui_designer_agent.process_task({
        "action": "create_component",
        "component_type": "button",
        "framework": "react",
        "styling": "tailwind",
        "props": {
            "variant": "primary",
            "size": "large",
            "onClick": "handleClick"
        },
        "requirements": {
            "accessible": True,
            "responsive": True
        }
    })
    
    if result.get("success"):
        print("✅ Component created successfully!")
        print(f"Component file: {result.get('filename', 'Button.jsx')}")
        print("\nGenerated code preview:")
        print(result.get("component_code", "")[:200] + "...")
    else:
        print(f"❌ Failed to create component: {result.get('error')}")
    print()

async def example_3_create_new_agent():
    """Example 3: Create a new specialized agent"""
    print("🤖 Example 3: Create New Agent")
    print("-" * 50)
    
    result = await agent_maker.process_task({
        "action": "create_agent",
        "agent_type": "content_writer",
        "requirements": {
            "specialization": "technical_writing",
            "experience_level": "senior",
            "skills": ["documentation", "api_docs", "tutorials"],
            "tone": "professional_friendly"
        }
    })
    
    if result.get("success"):
        print("✅ New agent created successfully!")
        print(f"Agent ID: {result.get('agent_id')}")
        print(f"Agent Type: {result.get('agent_type')}")
        print(f"Capabilities: {', '.join(result.get('capabilities', []))}")
    else:
        print(f"❌ Failed to create agent: {result.get('error')}")
    print()

async def example_4_build_fullstack_app():
    """Example 4: Build a complete full-stack application"""
    print("🚀 Example 4: Build Full-Stack App")
    print("-" * 50)
    
    # Step 1: Create project structure
    print("Step 1: Creating project structure...")
    project_result = await dev_engine_agent.process_task({
        "action": "create_project",
        "project_type": "fullstack_web",
        "name": "task_manager",
        "tech_stack": {
            "frontend": "react",
            "backend": "fastapi",
            "database": "postgresql",
            "styling": "tailwind"
        }
    })
    
    if project_result.get("success"):
        print("✅ Project structure created")
        
        # Step 2: Create API endpoints
        print("Step 2: Creating API endpoints...")
        api_result = await fullstack_dev_agent.process_task({
            "action": "create_api",
            "framework": "fastapi",
            "endpoints": [
                {"path": "/tasks", "method": "GET", "description": "Get all tasks"},
                {"path": "/tasks", "method": "POST", "description": "Create new task"},
                {"path": "/tasks/{id}", "method": "PUT", "description": "Update task"},
                {"path": "/tasks/{id}", "method": "DELETE", "description": "Delete task"}
            ],
            "models": [
                {
                    "name": "Task",
                    "fields": {
                        "id": "Integer",
                        "title": "String",
                        "description": "Text",
                        "completed": "Boolean",
                        "created_at": "DateTime"
                    }
                }
            ]
        })
        
        if api_result.get("success"):
            print("✅ API endpoints created")
            
            # Step 3: Create frontend components
            print("Step 3: Creating frontend components...")
            ui_result = await ui_designer_agent.process_task({
                "action": "create_page",
                "page_type": "task_dashboard",
                "components": ["task_list", "task_form", "task_item"],
                "framework": "react",
                "styling": "tailwind"
            })
            
            if ui_result.get("success"):
                print("✅ Frontend components created")
                print("🎉 Full-stack application ready!")
                print(f"Project files: {len(project_result.get('files', []))} files created")
            else:
                print(f"❌ UI creation failed: {ui_result.get('error')}")
        else:
            print(f"❌ API creation failed: {api_result.get('error')}")
    else:
        print(f"❌ Project creation failed: {project_result.get('error')}")
    print()

async def example_5_deploy_application():
    """Example 5: Deploy application to multiple platforms"""
    print("🌐 Example 5: Deploy Application")
    print("-" * 50)
    
    # Deploy to Netlify (frontend)
    print("Deploying to Netlify...")
    netlify_result = await deploy_manager_agent.process_task({
        "action": "deploy",
        "platform": "netlify",
        "app_name": "task-manager-frontend",
        "project_path": "./task_manager/frontend",
        "config": {
            "build_dir": "build",
            "build_command": "npm run build"
        }
    })
    
    if netlify_result.get("success"):
        print(f"✅ Frontend deployed to: {netlify_result.get('url', 'Netlify')}")
    else:
        print(f"⚠️ Netlify deployment: {netlify_result.get('error', 'Simulated')}")
    
    # Deploy to Railway (backend)
    print("Deploying to Railway...")
    railway_result = await deploy_manager_agent.process_task({
        "action": "deploy",
        "platform": "railway",
        "app_name": "task-manager-api",
        "project_path": "./task_manager/backend",
        "config": {
            "start_command": "uvicorn main:app --host 0.0.0.0 --port $PORT"
        }
    })
    
    if railway_result.get("success"):
        print(f"✅ Backend deployed to: {railway_result.get('url', 'Railway')}")
    else:
        print(f"⚠️ Railway deployment: {railway_result.get('error', 'Simulated')}")
    
    print("🎉 Application deployed to production!")
    print()

async def example_6_ai_prompt_optimization():
    """Example 6: AI prompt optimization"""
    print("📝 Example 6: AI Prompt Optimization")
    print("-" * 50)
    
    # Import prompt generator
    from agents.prompt_generator import prompt_generator_agent
    
    # Generate optimized prompt for code generation
    result = await prompt_generator_agent.process_task({
        "action": "generate_prompt",
        "task_type": "code_generation",
        "domain": "web_development",
        "target_model": "gpt-4",
        "requirements": {
            "role": "senior_react_developer",
            "task_description": "Create reusable React components with TypeScript",
            "output_format": "Complete component files with props interface",
            "constraints": "Follow React best practices and accessibility guidelines",
            "examples": True,
            "reasoning_required": True
        }
    })
    
    if result.get("success"):
        print("✅ Optimized prompt generated!")
        print(f"Prompt ID: {result.get('prompt_id')}")
        print(f"Pattern used: {result.get('pattern_used')}")
        print(f"Optimization techniques: {', '.join(result.get('optimization_techniques', []))}")
        print("\nGenerated prompt preview:")
        print(result.get("generated_prompt", "")[:300] + "...")
    else:
        print(f"❌ Prompt generation failed: {result.get('error')}")
    print()

async def example_7_prompt_master_coordination():
    """Example 7: Central coordination through Prompt Master"""
    print("🧠 Example 7: Prompt Master Coordination")
    print("-" * 50)
    
    # Process complex request through central coordinator
    result = await prompt_master.process_prompt(
        "Create a complete web application for a todo list with React frontend, FastAPI backend, and deploy it to Netlify and Railway",
        input_type="natural_language",
        metadata={
            "user_preference": "modern_design",
            "complexity": "medium",
            "deadline": "1_day"
        }
    )
    
    if result.get("success"):
        print("✅ Complex request processed!")
        print(f"Selected agents: {', '.join(result.get('agents_involved', []))}")
        print(f"Execution plan: {result.get('execution_summary', 'Multi-step workflow')}")
        print(f"Estimated time: {result.get('estimated_time', 'Unknown')}")
    else:
        print(f"❌ Processing failed: {result.get('error')}")
    print()

async def example_8_database_operations():
    """Example 8: Database synchronization and management"""
    print("💾 Example 8: Database Operations")
    print("-" * 50)
    
    # Import data sync agent
    from agents.data_sync import data_sync_agent
    
    # Create backup
    backup_result = await data_sync_agent.process_task({
        "action": "create_backup",
        "database_url": "sqlite:///data/agentic.db",
        "backup_path": "./backups/",
        "compression": True
    })
    
    if backup_result.get("success"):
        print("✅ Database backup created")
        print(f"Backup file: {backup_result.get('backup_file', 'backup.sql')}")
    else:
        print(f"⚠️ Backup simulation: {backup_result.get('error', 'Demo mode')}")
    
    # Get database statistics
    stats_result = await data_sync_agent.process_task({
        "action": "get_statistics",
        "database_url": "sqlite:///data/agentic.db"
    })
    
    if stats_result.get("success"):
        print("📊 Database statistics:")
        stats = stats_result.get("statistics", {})
        for table, count in stats.items():
            print(f"  {table}: {count} records")
    else:
        print("⚠️ Statistics not available in demo mode")
    print()

async def main():
    """Run all examples"""
    print("🧠 Agentic AI System - Usage Examples")
    print("🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia")
    print("=" * 60)
    print()
    
    examples = [
        example_1_basic_shell_commands,
        example_2_create_react_component,
        example_3_create_new_agent,
        example_4_build_fullstack_app,
        example_5_deploy_application,
        example_6_ai_prompt_optimization,
        example_7_prompt_master_coordination,
        example_8_database_operations
    ]
    
    for i, example in enumerate(examples, 1):
        try:
            await example()
        except Exception as e:
            print(f"❌ Example {i} failed: {e}")
            print()
        
        # Small delay between examples
        if i < len(examples):
            await asyncio.sleep(1)
    
    print("🎉 All examples completed!")
    print("\nNext steps:")
    print("- Run './run.sh start' to launch the full system")
    print("- Access web interface at http://localhost:5000")
    print("- Check documentation for advanced usage")

if __name__ == "__main__":
    asyncio.run(main())
