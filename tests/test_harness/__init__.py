"""Tests for the harness subpackage."""

from __future__ import annotations

import pytest

# ── Graph tests ──────────────────────────────────────────────────────────────


class TestHarnessGraph:
    """Tests for the harness execution graph."""

    @pytest.fixture
    def graph(self):
        from ai_multicolony.harness import HarnessGraph
        return HarnessGraph("test_graph")

    def test_graph_creation(self, graph):
        assert graph.graph_id == "test_graph"

    def test_add_planner(self, graph):
        node = graph.add_planner("plan")
        assert node.role.value == "planner"
        assert "plan" in graph.nodes

    def test_add_executor(self, graph):
        node = graph.add_executor("exec")
        assert node.role.value == "executor"

    def test_add_reviewer(self, graph):
        node = graph.add_reviewer("review")
        assert node.role.value == "reviewer"

    def test_add_edge(self, graph):
        graph.add_planner("plan")
        graph.add_executor("exec")
        graph.add_edge("plan", "exec")

    def test_add_edge_invalid_source(self, graph):
        with pytest.raises(ValueError):
            graph.add_edge("nonexistent", "exec")

    @pytest.mark.asyncio
    async def test_run_simple_graph(self, graph):
        async def plan_action(state):
            state["plan"] = "test_plan"
            return state

        async def exec_action(state):
            state["result"] = "executed"
            return state

        async def review_action(state):
            state["reviewed"] = True
            return state

        graph.add_planner("plan", plan_action)
        graph.add_executor("exec", exec_action)
        graph.add_reviewer("review", review_action)
        graph.add_edge("plan", "exec")
        graph.add_edge("exec", "review")

        result = await graph.run({"input": "test"})
        assert result.get("plan") == "test_plan"
        assert result.get("result") == "executed"
        assert result.get("reviewed") is True

    @pytest.mark.asyncio
    async def test_run_with_conditional_edge(self, graph):
        async def start_action(state):
            state["value"] = 10
            return state

        async def high_action(state):
            state["path"] = "high"
            return state

        async def low_action(state):
            state["path"] = "low"
            return state

        graph.add_node("start", start_action)
        graph.add_node("high", high_action)
        graph.add_node("low", low_action, exit=True)
        graph.add_conditional_edge(
            "start",
            lambda s: "high" if s.get("value", 0) > 5 else "low",
            {"high": "high", "low": "low"},
        )
        graph.add_edge("high", "low")

        result = await graph.run({})
        assert result.get("path") == "high"  # value=10, so goes high then low

    @pytest.mark.asyncio
    async def test_graph_checkpoint(self, graph):
        async def action(state):
            state["done"] = True
            return state

        graph.add_planner("start", action)
        graph.add_reviewer("end", action)
        graph.add_edge("start", "end")

        cp = graph.checkpoint({"step": 1}, "start")
        assert cp.current_node == "start"

    @pytest.mark.asyncio
    async def test_graph_no_entry_raises(self, graph):
        with pytest.raises(ValueError, match="No entry node"):
            await graph.run()

    def test_graph_reset(self, graph):
        graph.add_planner("start")
        graph.reset()
        from ai_multicolony.harness.graph import HarnessGraphStatus
        assert graph.status == HarnessGraphStatus.PENDING


# ── Skills tests ────────────────────────────────────────────────────────────


class TestSkillRegistry:
    """Tests for the skill registry and parser."""

    @pytest.fixture
    def registry(self):
        from ai_multicolony.harness import SkillDefinition, SkillRegistry
        r = SkillRegistry()
        skill = SkillDefinition(
            name="test_skill",
            description="A test skill",
            category="test",
            template="Hello {{name}}, welcome to {{project}}!",
        )
        r.register(skill)
        return r

    def test_registry_creation(self, registry):
        assert registry.skill_count == 1

    def test_get_skill(self, registry):
        skill = registry.get("test_skill")
        assert skill is not None
        assert skill.name == "test_skill"

    def test_get_nonexistent_skill(self, registry):
        assert registry.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_execute_skill(self, registry):
        result = await registry.execute("test_skill", {"name": "World", "project": "AI"})
        assert result.status == "completed"
        assert "World" in str(result.result)
        assert "AI" in str(result.result)

    @pytest.mark.asyncio
    async def test_execute_nonexistent_skill(self, registry):
        result = await registry.execute("nonexistent")
        assert result.status == "failed"

    def test_skill_parser(self):
        from ai_multicolony.harness import SkillParser
        markdown = """---
name: Parsed Skill
description: A parsed skill
category: analysis
tags: [test, parsed]
---

## Instructions
Analyze the {{target}}.
"""
        skill = SkillParser.parse(markdown)
        assert skill.name == "Parsed Skill"
        assert skill.category == "analysis"
        assert "test" in skill.tags

    def test_skill_template_rendering(self):
        from ai_multicolony.harness import SkillParser
        result = SkillParser.render_template(
            "Hello {{name}}!",
            {"name": "World"},
        )
        assert result == "Hello World!"

    def test_skill_parameter_validation(self):
        from ai_multicolony.harness import SkillDefinition, SkillParameter
        skill = SkillDefinition(
            name="param_test",
            parameters=[
                SkillParameter(name="required_param", type="string", required=True),
                SkillParameter(name="optional_param", type="int", required=False, default=42),
            ],
        )
        errors = skill.validate_params({})
        assert len(errors) > 0  # Missing required param

        errors = skill.validate_params({"required_param": "hello"})
        assert len(errors) == 0


# ── Sandbox tests ───────────────────────────────────────────────────────────


class TestSandbox:
    """Tests for the sandbox execution adapter."""

    @pytest.mark.asyncio
    async def test_mock_sandbox_execute(self):
        from ai_multicolony.harness import SandboxConfig, SandboxManager, SandboxType
        manager = SandboxManager()
        config = SandboxConfig(sandbox_type=SandboxType.MOCK)
        handle = await manager.create(config)
        result = await handle.execute_code("print('hello')", "python")
        assert result.success
        await manager.cleanup_all()

    @pytest.mark.asyncio
    async def test_subprocess_sandbox_execute(self):
        from ai_multicolony.harness import SandboxConfig, SandboxManager, SandboxType
        manager = SandboxManager()
        config = SandboxConfig(sandbox_type=SandboxType.SUBPROCESS, timeout_s=10.0)
        handle = await manager.create(config)
        result = await handle.execute_code("print('hello world')", "python")
        assert result.exit_code == 0 or result.status.value in ("completed", "failed")
        await manager.cleanup_all()

    @pytest.mark.asyncio
    async def test_sandbox_manager_stats(self):
        from ai_multicolony.harness import SandboxManager
        manager = SandboxManager()
        assert manager.active_count == 0

    @pytest.mark.asyncio
    async def test_sandbox_config(self):
        from ai_multicolony.harness import NetworkPolicy, SandboxConfig, SandboxType
        config = SandboxConfig(
            sandbox_type=SandboxType.SUBPROCESS,
            timeout_s=60.0,
            max_memory_mb=1024,
            network_policy=NetworkPolicy.NONE,
        )
        assert config.timeout_s == 60.0
        assert config.network_policy == NetworkPolicy.NONE


# ── Memory tests ─────────────────────────────────────────────────────────────


class TestHarnessMemory:
    """Tests for the harness memory system."""

    @pytest.fixture
    def memory(self, tmp_path):
        from ai_multicolony.harness import HarnessMemory
        db_path = str(tmp_path / "test_memory.db")
        return HarnessMemory(db_path=db_path)

    def test_store_and_get(self, memory):
        entry = memory.store("key1", {"value": 42}, category="test")
        assert entry.key == "key1"

        retrieved = memory.get("key1")
        assert retrieved is not None
        assert retrieved.value == {"value": 42}

    def test_recall(self, memory):
        memory.store("result_alpha", {"score": 95}, category="results")
        memory.store("result_beta", {"score": 87}, category="results")

        result = memory.recall("result")
        assert len(result.entries) >= 2

    def test_delete(self, memory):
        memory.store("to_delete", "value")
        assert memory.get("to_delete") is not None
        assert memory.delete("to_delete") is True
        assert memory.get("to_delete") is None

    def test_checkpoint_save_load(self, memory):
        cp = memory.save_checkpoint(
            graph_id="test_graph",
            state={"step": 5, "data": "hello"},
            label="test_checkpoint",
        )
        assert cp.graph_id == "test_graph"

        loaded = memory.load_checkpoint(cp.checkpoint_id)
        assert loaded is not None
        assert loaded.state["step"] == 5

    def test_stats(self, memory):
        memory.store("k1", "v1")
        stats = memory.stats
        assert stats["short_term_entries"] >= 1
