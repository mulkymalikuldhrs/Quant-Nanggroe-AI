"""Unit tests for DRL trading agents (engine/rl)."""

from __future__ import annotations

import numpy as np
import pytest

from quant_nanggroe.engine.rl import create_agent
from quant_nanggroe.engine.rl.agents import (
    BaseRLAgent,
    DQNAgent,
    Experience,
    PPOAgent,
    ReplayBuffer,
    RLState,
    SACAgent,
    TradingEnv,
)


class TestRLState:
    def test_to_array_shape(self):
        st = RLState.from_random(state_dim=10)
        assert st.to_array().shape == (10,)

    def test_from_random_dims(self):
        # regression: from_random must honour state_dim (bug: clamped to 8 for dim<8)
        # documented layout: prices(2)+volumes(2)+indicators(state_dim-7)+3 → min length 7
        for d in (7, 8, 10, 20):
            st = RLState.from_random(state_dim=d)
            assert len(st.to_array()) == d
        # document the floor: a <7 request is clamped to a valid 7-length state
        assert len(RLState.from_random(state_dim=4).to_array()) == 7


class TestReplayBuffer:
    def test_push_sample(self):
        buf = ReplayBuffer(capacity=3)
        for i in range(5):
            buf.push(Experience(state=np.array([i]), action=0, reward=0.0, next_state=np.array([i]), done=False))
        assert len(buf) == 3  # capped at capacity
        batch = buf.sample(2)
        assert len(batch) == 2

    def test_sample_under_capacity(self):
        buf = ReplayBuffer(capacity=10)
        buf.push(Experience(state=np.array([0]), action=0, reward=0.0, next_state=np.array([0]), done=False))
        with pytest.raises(ValueError):  # replace=False over full population
            buf.sample(2)


class TestCreateAgent:
    @pytest.mark.parametrize("name", ["ppo", "dqn", "sac"])
    def test_create(self, name):
        agent = create_agent(name, state_dim=10, action_dim=3, learning_rate=3e-4)
        assert agent is not None
        st = RLState.from_random(state_dim=10)
        action = agent.act(st)
        assert action is not None

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            create_agent("invalid", state_dim=10, action_dim=3)


class TestBaseAgentFallbacks:
    def test_act_update_fallback(self):
        a = BaseRLAgent(state_dim=4, action_dim=2)
        assert a.act(RLState.from_random(4)) == 0
        assert a.update([Experience(np.zeros(4), 0, 0.0, np.zeros(4), False)]) == {}


class TestPPO:
    def test_act(self):
        a = PPOAgent(state_dim=10, action_dim=3)
        act = a.act(RLState.from_random(state_dim=10))
        # PPO act on a discrete agent returns a class index in [0, action_dim)
        assert 0 <= act <= 2

    def test_update(self):
        a = PPOAgent(state_dim=10, action_dim=2)
        exps = [Experience(np.random.randn(10), np.array([0.1]), 0.5, np.random.randn(10), False)
                for _ in range(8)]
        out = a.update(exps)
        assert "policy_loss" in out and "value_loss" in out
        assert a.metrics.episodes == 1


class TestDQNTraining:
    def test_update(self):
        agent = create_agent("dqn", state_dim=4, action_dim=2)
        exp = Experience(state=np.zeros(4), action=0, reward=1.0, next_state=np.zeros(4), done=False)
        for _ in range(5):
            losses = agent.update([exp])
        assert isinstance(losses, dict)
        assert "q_loss" in losses


class TestSAC:
    def test_act(self):
        a = SACAgent(state_dim=10, action_dim=3)
        act = a.act(RLState.from_random(state_dim=10), deterministic=True)
        assert isinstance(act, np.ndarray)
        assert len(act) == 3

    def test_update(self):
        a = SACAgent(state_dim=4, action_dim=1, batch_size=4)
        for _ in range(5):
            a.update([Experience(np.random.randn(4), np.array([0.1]), 0.5, np.random.randn(4), False)])
        assert a.metrics.episodes >= 1


class TestTradingEnv:
    def test_reset_step(self):
        prices = np.linspace(100, 120, 50)
        env = TradingEnv(prices=prices, window_size=10)
        st = env.reset()
        assert isinstance(st, RLState)
        ns, reward, done = env.step(1)  # buy
        assert isinstance(ns, RLState)
        assert np.isfinite(reward)

    def test_rsi(self):
        prices = np.linspace(100, 110, 30)
        assert 0 <= TradingEnv._rsi(prices) <= 100

    def test_runs_to_end(self):
        prices = np.linspace(100, 120, 30)
        env = TradingEnv(prices=prices, window_size=5)
        env.reset()
        steps = 0
        while True:
            _, _, done = env.step(np.random.choice([0, 1, 2]))
            steps += 1
            if done:
                break
        assert steps > 0
