"""CLI interface for AI MultiColony Ecosystem.

Provides the `amce` command with subcommands:
- serve: Start the API server
- agent: Run and manage agents
- colony: Manage colonies
- tool: List and inspect tools
- memory: Inspect and query memory
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_multicolony import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="amce")
def main() -> None:
    """AI MultiColony Ecosystem - Colony-based Agent Operating System.

    Use 'amce serve' to start the API server, or 'amce agent run' to
    execute a single agent task.
    """
    pass


# === Serve Command ===


@main.command()
@click.option("--host", default="0.0.0.0", help="API server host")
@click.option("--port", default=8000, type=int, help="API server port")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--workers", default=1, type=int, help="Number of workers")
@click.option("--log-level", default="info", type=click.Choice(["debug", "info", "warning", "error"]))
def serve(host: str, port: int, reload: bool, workers: int, log_level: str) -> None:
    """Start the API server."""
    from ai_multicolony.config.settings import get_settings
    from ai_multicolony.config.logging_config import setup_logging

    settings = get_settings()
    setup_logging(level=log_level.upper())
    settings.apply_to_env()

    console.print(Panel.fit(
        f"[bold green]AI MultiColony Ecosystem v{__version__}[/bold green]\n"
        f"Starting API server on [cyan]{host}:{port}[/cyan]\n"
        f"Environment: [yellow]{settings.app_env}[/yellow]\n"
        f"Workers: {workers}",
        title="AMCE Server",
    ))

    try:
        import uvicorn

        uvicorn.run(
            "ai_multicolony.api.app:create_app",
            host=host,
            port=port,
            reload=reload,
            workers=workers,
            factory=True,
            log_level=log_level,
        )
    except ImportError:
        console.print("[red]uvicorn not installed. Install with: pip install uvicorn[/red]")
        sys.exit(1)


# === Agent Commands ===


@main.group()
def agent() -> None:
    """Run and manage agents."""
    pass


@agent.command("run")
@click.option("--type", "-t", "agent_type", default="manus", help="Agent type to run")
@click.option("--task", "-k", required=True, help="Task description")
@click.option("--model", "-m", default="gpt-4o", help="LLM model to use")
@click.option("--colony", "-c", help="Colony ID to run in")
@click.option("--config", "config_path", type=click.Path(exists=True), help="Config file path")
@click.option("--max-iterations", default=10, type=int, help="Maximum agent iterations")
def agent_run(
    agent_type: str,
    task: str,
    model: str,
    colony: Optional[str],
    config_path: Optional[str],
    max_iterations: int,
) -> None:
    """Run an agent with a task."""
    from ai_multicolony.config.settings import get_settings
    from ai_multicolony.config.logging_config import setup_logging

    settings = get_settings(config_path)
    setup_logging(level=settings.log_level)
    settings.apply_to_env()

    console.print(f"[bold blue]Running agent:[/bold blue] [cyan]{agent_type}[/cyan]")
    console.print(f"[bold blue]Task:[/bold blue] {task}")
    console.print(f"[bold blue]Model:[/bold blue] {model}")

    if colony:
        console.print(f"[bold blue]Colony:[/bold blue] [cyan]{colony}[/cyan]")
        asyncio.run(_run_colony(colony, task, model, max_iterations, settings))
    else:
        asyncio.run(_run_agent(agent_type, task, model, max_iterations, settings))


@agent.command("list")
def agent_list() -> None:
    """List available agent types."""
    table = Table(title="Available Agent Types")
    table.add_column("Role", style="cyan")
    table.add_column("Description", style="green")

    from ai_multicolony.types.agent import AgentRole

    descriptions = {
        AgentRole.MANUS: "General-purpose agent with full tool access",
        AgentRole.PLANNER: "Task decomposition and planning specialist",
        AgentRole.EXECUTOR: "Task execution specialist",
        AgentRole.CODER: "Code generation and review specialist",
        AgentRole.BROWSER: "Web browsing and interaction specialist",
        AgentRole.VOICE: "Voice input/output specialist",
        AgentRole.SECURITY: "Security analysis specialist",
        AgentRole.RESEARCHER: "Information gathering and analysis specialist",
        AgentRole.COLONY: "Colony management specialist",
        AgentRole.SUPERVISOR: "Agent supervision and coordination",
        AgentRole.WORKER: "General worker agent",
    }

    for role in AgentRole:
        table.add_row(role.value, descriptions.get(role, ""))

    console.print(table)


@agent.command("status")
@click.option("--agent-id", "-a", required=True, help="Agent ID to inspect")
def agent_status(agent_id: str) -> None:
    """Show agent status."""
    console.print(f"[yellow]Agent status for {agent_id} requires a running server.[/yellow]")
    console.print("Use [cyan]amce serve[/cyan] to start the API server first.")


# === Colony Commands ===


@main.group()
def colony() -> None:
    """Manage colonies."""
    pass


@colony.command("create")
@click.option("--name", "-n", required=True, help="Colony name")
@click.option("--model", "-m", default="gpt-4o", help="Default model for colony agents")
@click.option("--max-agents", default=10, type=int, help="Maximum agents in colony")
@click.option("--max-cost", default=50.0, type=float, help="Maximum cost in USD")
def colony_create(name: str, model: str, max_agents: int, max_cost: float) -> None:
    """Create a new colony."""
    from ai_multicolony.types.colony import ColonyConfig, ColonyState

    config = ColonyConfig(
        name=name,
        model=model,
        max_agents=max_agents,
        max_cost=max_cost,
        state=ColonyState.IDLE,
    )

    console.print(Panel.fit(
        f"[bold green]Colony Created[/bold green]\n"
        f"ID: [cyan]{config.colony_id}[/cyan]\n"
        f"Name: {config.name}\n"
        f"Model: {config.model}\n"
        f"Max Agents: {config.max_agents}\n"
        f"Max Cost: ${config.max_cost:.2f}",
        title="Colony",
    ))


@colony.command("list")
def colony_list() -> None:
    """List colonies (requires running server)."""
    console.print("[yellow]Colony listing requires a running server.[/yellow]")
    console.print("Use [cyan]amce serve[/cyan] to start the API server first.")


@colony.command("status")
@click.option("--colony-id", "-c", required=True, help="Colony ID to inspect")
def colony_status(colony_id: str) -> None:
    """Show colony status."""
    console.print(f"[yellow]Colony status for {colony_id} requires a running server.[/yellow]")
    console.print("Use [cyan]amce serve[/cyan] to start the API server first.")


# === Tool Commands ===


@main.group()
def tool() -> None:
    """List and inspect tools."""
    pass


@tool.command("list")
def tool_list() -> None:
    """List available tools."""
    from ai_multicolony.core.tool_registry import ToolRegistry
    from ai_multicolony.types.tools import ToolType

    registry = ToolRegistry.get_instance()
    all_tools = registry.list_all()

    if not all_tools:
        console.print("[yellow]No tools registered.[/yellow]")
        console.print("Tools are registered when agents are created or via the API.")
        return

    table = Table(title="Registered Tools")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="green")
    table.add_column("Tags", style="yellow")

    for name, info in all_tools.items():
        table.add_row(
            name,
            info.get("tool_type", ""),
            info.get("description", "")[:60],
            ", ".join(info.get("tags", [])),
        )

    console.print(table)


@tool.command("inspect")
@click.argument("tool_name")
def tool_inspect(tool_name: str) -> None:
    """Inspect a specific tool's schema."""
    from ai_multicolony.core.tool_registry import ToolRegistry

    registry = ToolRegistry.get_instance()
    try:
        t = registry.get(tool_name)
        schema = t.get_openai_schema()

        import json
        console.print(Panel.fit(
            f"[bold cyan]{t.name}[/bold cyan]\n"
            f"Type: {t.tool_type.value}\n"
            f"Description: {t.description}\n"
            f"Tags: {', '.join(t.tags)}\n\n"
            f"[bold]OpenAI Schema:[/bold]\n"
            f"{json.dumps(schema, indent=2)}",
            title="Tool Inspector",
        ))
    except KeyError:
        console.print(f"[red]Tool '{tool_name}' not found.[/red]")


@tool.command("types")
def tool_types() -> None:
    """List available tool types."""
    from ai_multicolony.types.tools import ToolType

    table = Table(title="Tool Types")
    table.add_column("Type", style="cyan")
    table.add_column("Description", style="green")

    descriptions = {
        ToolType.SHELL: "Shell command execution",
        ToolType.FILE: "File read/write operations",
        ToolType.BROWSER: "Web browser automation",
        ToolType.SEARCH: "Web search",
        ToolType.CODE: "Code execution",
        ToolType.MCP: "MCP protocol tools",
        ToolType.DOCKER: "Docker container management",
        ToolType.VOICE: "Voice input/output",
        ToolType.MEMORY: "Memory operations",
        ToolType.CHANNEL: "Channel communication",
    }

    for tt in ToolType:
        table.add_row(tt.value, descriptions.get(tt, ""))

    console.print(table)


# === Memory Commands ===


@main.group()
def memory() -> None:
    """Inspect and query memory."""
    pass


@memory.command("stats")
def memory_stats() -> None:
    """Show memory system statistics."""
    from ai_multicolony.core.memory_manager import MemoryManager

    manager = MemoryManager()
    stats = manager.get_stats()

    table = Table(title="Memory Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    for key, value in stats.items():
        table.add_row(str(key), str(value))

    console.print(table)


@memory.command("condensers")
def memory_condensers() -> None:
    """List available memory condensers."""
    from ai_multicolony.types.memory import CondenserType

    table = Table(title="Memory Condensers")
    table.add_column("Type", style="cyan")
    table.add_column("Description", style="green")

    descriptions = {
        CondenserType.NOOP: "No condensation - pass through unchanged",
        CondenserType.RECENT: "Keep only the most recent N events",
        CondenserType.OBSERVATION: "Keep only observations, discard intermediate actions",
        CondenserType.LLM: "LLM-based summarization of events",
        CondenserType.AMORTIZED: "Amortized forgetting with importance decay",
        CondenserType.BROWSER_OUTPUT: "Truncate long browser output",
        CondenserType.LLMLINGUA: "Token compression (simplified)",
        CondenserType.EVENT_MASK: "Filter out irrelevant event types",
    }

    for ct in CondenserType:
        table.add_row(ct.value, descriptions.get(ct, ""))

    console.print(table)


@memory.command("types")
def memory_types() -> None:
    """List memory types."""
    from ai_multicolony.types.memory import MemoryType

    table = Table(title="Memory Types")
    table.add_column("Type", style="cyan")
    table.add_column("Description", style="green")

    descriptions = {
        MemoryType.EPISODIC: "Specific events and experiences",
        MemoryType.SEMANTIC: "General knowledge and facts",
        MemoryType.PROCEDURAL: "How-to knowledge and skills",
        MemoryType.WORKING: "Short-term active context",
        MemoryType.CONVERSATION: "Conversation history",
        MemoryType.TOOL_HISTORY: "Tool execution history",
        MemoryType.PLAN: "Plans and goals",
    }

    for mt in MemoryType:
        table.add_row(mt.value, descriptions.get(mt, ""))

    console.print(table)


# === Helper Functions ===


async def _run_agent(agent_type: str, task: str, model: str, max_iterations: int, settings: object) -> None:
    """Run a single agent with a task."""
    try:
        from ai_multicolony.agents.registry import AgentRegistry
        from ai_multicolony.core.base_agent import BaseAgent
        from ai_multicolony.types.agent import AgentConfig, AgentRole

        # Try the registry first, fall back to BaseAgent directly
        try:
            registry = AgentRegistry()
            agent_cls = registry.get(agent_type)
            agent_instance = agent_cls(
                config=AgentConfig(
                    role=AgentRole(agent_type),
                    model=model,
                    max_iterations=max_iterations,
                )
            )
        except Exception:
            console.print(f"[yellow]Agent type '{agent_type}' not in registry, using BaseAgent.[/yellow]")
            agent_instance = BaseAgent(
                config=AgentConfig(
                    role=AgentRole(agent_type) if agent_type in [r.value for r in AgentRole] else AgentRole.MANUS,
                    model=model,
                    max_iterations=max_iterations,
                )
            )

        result = await agent_instance.run(task)
        console.print(f"\n[bold green]Result:[/bold green] {result}")

        # Show output metrics
        output = agent_instance.get_output()
        console.print(f"\n[dim]Iterations: {output.iterations} | "
                     f"Tokens: {output.tokens_used} | "
                     f"Cost: ${output.cost_incurred:.4f}[/dim]")

    except Exception as e:
        console.print(f"[red]Agent error: {e}[/red]")
        sys.exit(1)


async def _run_colony(colony_id: str, task: str, model: str, max_iterations: int, settings: object) -> None:
    """Run a colony with a task."""
    try:
        from ai_multicolony.colony.manager import ColonyManager

        manager = ColonyManager()
        colony = await manager.get_or_create(colony_id, model=model)
        result = await colony.run(task)
        console.print(f"\n[bold green]Colony Result:[/bold green] {result}")
    except Exception as e:
        console.print(f"[red]Colony error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
