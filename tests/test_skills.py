"""Tests: Vibe-Trading skill taxonomy — registry, technical skills, swarm presets."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from quant_nanggroe.skills.registry import SkillCategory, SkillDef, SkillRegistry
from quant_nanggroe.skills.swarm_presets import SWARM_PRESETS, SwarmPreset, get_preset, list_presets
from quant_nanggroe.skills.technical_skills import register_technical_skills


class TestSkillCategory(unittest.TestCase):
    """Tests for SkillCategory enum."""

    def test_has_all_categories(self):
        expected = {"technical", "fundamental", "sentiment", "risk", "execution", "analysis"}
        actual = {c.value for c in SkillCategory}
        self.assertEqual(expected, actual)

    def test_technical_value(self):
        self.assertEqual(SkillCategory.TECHNICAL.value, "technical")

    def test_risk_value(self):
        self.assertEqual(SkillCategory.RISK.value, "risk")


class TestSkillDef(unittest.TestCase):
    """Tests for SkillDef dataclass."""

    def test_default_params_empty_dict(self):
        sd = SkillDef(name="test", category=SkillCategory.TECHNICAL, description="test")
        self.assertEqual(sd.params, {})

    def test_default_dependencies_empty_list(self):
        sd = SkillDef(name="test", category=SkillCategory.TECHNICAL, description="test")
        self.assertEqual(sd.dependencies, [])

    def test_custom_params(self):
        sd = SkillDef(
            name="rsi",
            category=SkillCategory.TECHNICAL,
            description="RSI analysis",
            params={"period": 14},
        )
        self.assertEqual(sd.params["period"], 14)

    def test_with_dependencies(self):
        sd = SkillDef(
            name="composite",
            category=SkillCategory.ANALYSIS,
            description="composite",
            dependencies=["sma", "rsi"],
        )
        self.assertEqual(sd.dependencies, ["sma", "rsi"])


class TestSkillRegistry(unittest.TestCase):
    """Tests for SkillRegistry."""

    def setUp(self):
        self.registry = SkillRegistry()

    def test_initial_empty(self):
        self.assertEqual(self.registry.skills, {})

    def test_register_adds_skill(self):
        sd = SkillDef(name="test", category=SkillCategory.TECHNICAL, description="test skill")
        self.registry.register(sd)
        self.assertIn("test", self.registry.skills)
        self.assertIs(self.registry.skills["test"], sd)

    def test_register_overwrites_duplicate(self):
        sd1 = SkillDef(name="dup", category=SkillCategory.TECHNICAL, description="first")
        sd2 = SkillDef(name="dup", category=SkillCategory.RISK, description="second")
        self.registry.register(sd1)
        self.registry.register(sd2)
        self.assertIs(self.registry.skills["dup"], sd2)

    def test_get_by_category_filters(self):
        sd_tech = SkillDef(name="t1", category=SkillCategory.TECHNICAL, description="tech")
        sd_risk = SkillDef(name="r1", category=SkillCategory.RISK, description="risk")
        self.registry.register(sd_tech)
        self.registry.register(sd_risk)
        tech_skills = self.registry.get_by_category(SkillCategory.TECHNICAL)
        self.assertEqual(tech_skills, [sd_tech])
        risk_skills = self.registry.get_by_category(SkillCategory.RISK)
        self.assertEqual(risk_skills, [sd_risk])

    def test_get_by_category_empty_when_none(self):
        result = self.registry.get_by_category(SkillCategory.FUNDAMENTAL)
        self.assertEqual(result, [])

    def test_get_dependency_chain_no_deps(self):
        sd = SkillDef(name="leaf", category=SkillCategory.TECHNICAL, description="leaf")
        self.registry.register(sd)
        chain = self.registry.get_dependency_chain("leaf")
        self.assertEqual(chain, ["leaf"])

    def test_get_dependency_chain_with_deps(self):
        leaf = SkillDef(name="leaf", category=SkillCategory.TECHNICAL, description="leaf")
        mid = SkillDef(name="mid", category=SkillCategory.ANALYSIS, description="mid", dependencies=["leaf"])
        top = SkillDef(name="top", category=SkillCategory.RISK, description="top", dependencies=["mid"])
        self.registry.register(leaf)
        self.registry.register(mid)
        self.registry.register(top)
        chain = self.registry.get_dependency_chain("top")
        self.assertEqual(chain, ["leaf", "mid", "top"])

    def test_get_dependency_chain_unknown_skill(self):
        chain = self.registry.get_dependency_chain("nonexistent")
        self.assertEqual(chain, [])

    def test_get_dependency_chain_handles_circular(self):
        a = SkillDef(name="a", category=SkillCategory.TECHNICAL, description="a", dependencies=["b"])
        b = SkillDef(name="b", category=SkillCategory.TECHNICAL, description="b", dependencies=["a"])
        self.registry.register(a)
        self.registry.register(b)
        chain = self.registry.get_dependency_chain("a")
        self.assertIn("a", chain)
        self.assertIn("b", chain)

    def test_compose_resolves_deps(self):
        leaf = SkillDef(name="leaf", category=SkillCategory.TECHNICAL, description="leaf")
        mid = SkillDef(name="mid", category=SkillCategory.ANALYSIS, description="mid", dependencies=["leaf"])
        self.registry.register(leaf)
        self.registry.register(mid)
        result = self.registry.compose(["mid"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "leaf")
        self.assertEqual(result[1].name, "mid")

    def test_compose_preserves_order(self):
        a = SkillDef(name="a", category=SkillCategory.TECHNICAL, description="a")
        b = SkillDef(name="b", category=SkillCategory.TECHNICAL, description="b")
        self.registry.register(a)
        self.registry.register(b)
        result = self.registry.compose(["a", "b"])
        self.assertEqual([s.name for s in result], ["a", "b"])

    def test_compose_with_unregistered_skill(self):
        leaf = SkillDef(name="leaf", category=SkillCategory.TECHNICAL, description="leaf")
        self.registry.register(leaf)
        result = self.registry.compose(["leaf", "nonexistent"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "leaf")

    def test_compose_empty_list(self):
        result = self.registry.compose([])
        self.assertEqual(result, [])

    def test_compose_dedup_shared_dep(self):
        base = SkillDef(name="base", category=SkillCategory.TECHNICAL, description="base")
        a = SkillDef(name="a", category=SkillCategory.ANALYSIS, description="a", dependencies=["base"])
        b = SkillDef(name="b", category=SkillCategory.RISK, description="b", dependencies=["base"])
        self.registry.register(base)
        self.registry.register(a)
        self.registry.register(b)
        result = self.registry.compose(["a", "b"])
        names = [s.name for s in result]
        self.assertEqual(names.count("base"), 1)
        self.assertIn("base", names)
        self.assertIn("a", names)
        self.assertIn("b", names)


class TestRegisterTechnicalSkills(unittest.TestCase):
    """Tests for register_technical_skills."""

    def setUp(self):
        self.registry = SkillRegistry()
        register_technical_skills(self.registry)

    def test_registers_expected_skills(self):
        expected = [
            "sma_crossover", "rsi_analysis", "macd_analysis", "bollinger_bands",
            "volume_analysis", "support_resistance", "trend_analysis",
            "volatility_analysis", "sentiment_score", "risk_calculator",
        ]
        for name in expected:
            self.assertIn(name, self.registry.skills, f"Missing skill: {name}")

    def test_all_categories_present(self):
        categories = {s.category for s in self.registry.skills.values()}
        for cat in (SkillCategory.TECHNICAL, SkillCategory.ANALYSIS, SkillCategory.RISK, SkillCategory.SENTIMENT):
            self.assertIn(cat, categories, f"Missing category: {cat}")

    def test_skill_counts_by_category(self):
        counts = {}
        for s in self.registry.skills.values():
            counts[s.category] = counts.get(s.category, 0) + 1
        self.assertGreaterEqual(counts.get(SkillCategory.TECHNICAL, 0), 4)
        self.assertGreaterEqual(counts.get(SkillCategory.ANALYSIS, 0), 2)
        self.assertGreaterEqual(counts.get(SkillCategory.RISK, 0), 2)

    def test_each_skill_has_description(self):
        for name, skill in self.registry.skills.items():
            self.assertTrue(skill.description, f"Skill {name} has empty description")


class TestSwarmPresets(unittest.TestCase):
    """Tests for swarm presets."""

    def test_preset_dataclass(self):
        p = SwarmPreset(name="Test", description="test preset", skills=["a", "b"])
        self.assertEqual(p.name, "Test")
        self.assertEqual(p.description, "test preset")
        self.assertEqual(p.skills, ["a", "b"])

    def test_default_config_empty_dict(self):
        p = SwarmPreset(name="Test", description="test", skills=[])
        self.assertEqual(p.config, {})

    def test_has_all_presets(self):
        expected = {"momentum_scalper", "trend_follower", "mean_reversion", "gold_strategy"}
        self.assertEqual(set(SWARM_PRESETS.keys()), expected)

    def test_get_preset_returns_preset(self):
        p = get_preset("momentum_scalper")
        self.assertIsInstance(p, SwarmPreset)
        self.assertEqual(p.name, "Momentum Scalper")

    def test_get_preset_invalid_raises(self):
        with self.assertRaises(ValueError):
            get_preset("nonexistent")

    def test_list_presets(self):
        presets = list_presets()
        self.assertEqual(sorted(presets), sorted(SWARM_PRESETS.keys()))

    def test_momentum_scalper_skills(self):
        p = get_preset("momentum_scalper")
        self.assertEqual(p.skills, ["rsi_analysis", "volume_analysis", "risk_calculator"])

    def test_trend_follower_skills(self):
        p = get_preset("trend_follower")
        self.assertEqual(p.skills, ["sma_crossover", "macd_analysis", "trend_analysis", "risk_calculator"])

    def test_mean_reversion_skills(self):
        p = get_preset("mean_reversion")
        self.assertEqual(p.skills, ["bollinger_bands", "rsi_analysis", "support_resistance", "risk_calculator"])

    def test_gold_strategy_skills(self):
        p = get_preset("gold_strategy")
        self.assertEqual(p.skills, ["volatility_analysis", "support_resistance", "sentiment_score"])

    def test_each_preset_has_config(self):
        for name, preset in SWARM_PRESETS.items():
            self.assertIn("timeframe", preset.config, f"Preset {name} missing timeframe")
            self.assertIn("min_confidence", preset.config, f"Preset {name} missing min_confidence")

    def test_gold_strategy_asset_config(self):
        p = get_preset("gold_strategy")
        self.assertEqual(p.config["asset"], "XAUUSD")


if __name__ == "__main__":
    unittest.main(verbosity=2)
