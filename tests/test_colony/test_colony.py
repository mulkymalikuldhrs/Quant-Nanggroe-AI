"""Tests for colony management."""
import pytest
from ai_multicolony.colony.manager import ColonyManager
from ai_multicolony.colony.hands import HandManager, SecurityHand, CodeHand
from ai_multicolony.colony.scheduler import TaskScheduler
from ai_multicolony.colony.a2a import A2ACoordinator
from ai_multicolony.types import Task, TaskPriority

class TestColonyManager:
    def test_create(self): assert ColonyManager() is not None
    def test_create_colony(self):
        cm = ColonyManager()
        colony = cm.create_colony()
        assert colony is not None

class TestHands:
    def test_manager(self): assert HandManager() is not None
    def test_security(self): assert SecurityHand().hand_type == "security"
    def test_code(self): assert CodeHand().hand_type == "code"

class TestTaskScheduler:
    def test_create(self): assert TaskScheduler() is not None
    def test_submit(self):
        ts = TaskScheduler()
        task = Task(description="Test", priority=TaskPriority.MEDIUM, required_capabilities=["test"])
        task_id = ts.submit(task)
        assert task_id is not None
    def test_stats(self):
        ts = TaskScheduler()
        stats = ts.get_stats()
        assert isinstance(stats, dict)

class TestA2A:
    def test_create(self): assert A2ACoordinator() is not None
    def test_register_agent(self):
        a = A2ACoordinator()
        a.register_agent(agent_id="a1", colony_id="c1", capabilities=["test"])
        cap = a.get_agent_capabilities("a1")
        assert cap is not None
    def test_stats(self):
        a = A2ACoordinator()
        stats = a.get_stats()
        assert isinstance(stats, dict)
