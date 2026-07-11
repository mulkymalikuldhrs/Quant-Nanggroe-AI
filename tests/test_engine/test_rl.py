"""Unit tests for DRL trading agents (engine/rl)."""

from __future__ import annotations

import numpy as np
import pytest

from quant_nanggroe.engine.rl import create_agent
from quant_nanggroe.engine.rl.agents import RLState, Experience


class TestRLState:
    def test_from_random_dimension(self):
        state = RLState.from_random(state_dim=10)
        arr = state.to_array()
        assert len(arr) == 10

    def test_from_random_higher_dim(self):
        state = RLState.from_random(state_dim=20)
        arr = state.to_array()
        assert len(arr) == 20


class TestCreateAgent:
    def test_create_ppo(self):
        agent = create_agent("ppo", state_dim=10, action_dim=3, learning_rate=3e-4)
        assert agent is not None
        state = RLState.from_random(state_dim=10)
        action = agent.act(state)
        assert 0 <= action <= 2

    def test_create_dqn(self):
        agent = create_agent("dqn", state_dim=10, action_dim=3, learning_rate=3e-4)
        assert agent is not None
        state = RLState.from_random(state_dim=10)
        action = agent.act(state)
        assert 0 <= action <= 2

    def test_create_sac(self):
        agent = create_agent("sac", state_dim=10, action_dim=3, learning_rate=3e-4)
        assert agent is not None
        state = RLState.from_random(state_dim=10)
        action = agent.act(state, deterministic=True)
        assert isinstance(action, np.ndarray)
        assert len(action) == 3

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            create_agent("invalid", state_dim=10, action_dim=3)


class TestDQNTraining:
    def test_update(self):
        agent = create_agent("dqn", state_dim=4, action_dim=2)
        state = RLState.from_random(state_dim=4)
        exp = Experience(
            state=state.to_array(),
            action=0,
            reward=1.0,
            next_state=state.to_array(),
            done=False,
        )
        for _ in range(5):
            losses = agent.update([exp])
        assert isinstance(losses, dict)
