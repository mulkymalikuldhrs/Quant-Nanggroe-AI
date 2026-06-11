"""Tests for all tool implementations."""
import pytest
from ai_multicolony.tools.shell import ShellTool
from ai_multicolony.tools.file import FileTool
from ai_multicolony.tools.browser import BrowserTool
from ai_multicolony.tools.search import SearchTool
from ai_multicolony.tools.code import CodeTool
from ai_multicolony.tools.docker import DockerTool
from ai_multicolony.tools.voice import VoiceTool
from ai_multicolony.tools.memory import MemoryTool
from ai_multicolony.tools.channel import ChannelTool
from ai_multicolony.tools.registry import ToolRegistry

class TestShellTool:
    def test_name(self): assert ShellTool().name() == "shell.execute"
    def test_category(self): assert ShellTool().category() == "compute"
    def test_autonomy(self): assert ShellTool().autonomy_level() >= 1
    def test_schema(self): assert isinstance(ShellTool().input_schema(), dict)
    def test_output_schema(self): assert isinstance(ShellTool().output_schema(), dict)
    def test_health_check(self): assert isinstance(ShellTool().health_check(), bool)

class TestFileTool:
    def test_category(self): assert FileTool().category() == "data"
    def test_autonomy(self): assert FileTool().autonomy_level() >= 0

class TestBrowserTool:
    def test_category(self): assert BrowserTool().category() == "browser"

class TestSearchTool:
    def test_autonomy(self): assert SearchTool().autonomy_level() == 0

class TestCodeTool:
    def test_category(self): assert CodeTool().category() == "compute"

class TestDockerTool:
    def test_category(self): assert DockerTool().category() == "sandbox"

class TestVoiceTool:
    def test_category(self): assert VoiceTool().category() == "voice"

class TestMemoryTool:
    def test_category(self): assert MemoryTool().category() == "memory"

class TestChannelTool:
    def test_category(self): assert ChannelTool().category() == "communication"

class TestToolRegistry:
    def test_create(self): assert ToolRegistry() is not None
    def test_register(self):
        r = ToolRegistry()
        r.register(ShellTool())
        assert r.get("shell.execute") is not None
    def test_tool_count(self):
        r = ToolRegistry()
        r.register(ShellTool())
        assert r.tool_count >= 1
    def test_list_tools(self):
        r = ToolRegistry()
        r.register(ShellTool())
        tools = r.list_tools()
        assert len(tools) >= 1
    def test_categories(self):
        r = ToolRegistry()
        r.register(ShellTool())
        cats = r.list_categories()
        assert isinstance(cats, (list, set, tuple, dict))
    def test_health_check(self):
        r = ToolRegistry()
        r.register(ShellTool())
        health = r.health_check()
        assert isinstance(health, dict)
    def test_stats(self):
        r = ToolRegistry()
        r.register(ShellTool())
        stats = r.get_stats()
        assert isinstance(stats, dict)
    def test_unregister(self):
        r = ToolRegistry()
        r.register(ShellTool())
        r.unregister("shell.execute")
        assert r.get("shell.execute") is None
