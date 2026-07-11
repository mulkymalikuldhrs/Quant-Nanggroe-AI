"""Vibe-Trading-inspired technical analysis skills."""
from .registry import SkillCategory, SkillDef, SkillRegistry


def register_technical_skills(registry: SkillRegistry):
    """Register 10+ technical analysis skills."""

    skills = [
        SkillDef(
            name="sma_crossover",
            category=SkillCategory.TECHNICAL,
            description="Simple Moving Average crossover signal",
            params={"fast_period": 5, "slow_period": 20},
        ),
        SkillDef(
            name="rsi_analysis",
            category=SkillCategory.TECHNICAL,
            description="Relative Strength Index analysis",
            params={"period": 14, "overbought": 70, "oversold": 30},
        ),
        SkillDef(
            name="macd_analysis",
            category=SkillCategory.TECHNICAL,
            description="MACD indicator analysis",
            params={"fast": 12, "slow": 26, "signal": 9},
        ),
        SkillDef(
            name="bollinger_bands",
            category=SkillCategory.TECHNICAL,
            description="Bollinger Bands volatility analysis",
            params={"period": 20, "std_dev": 2},
        ),
        SkillDef(
            name="volume_analysis",
            category=SkillCategory.ANALYSIS,
            description="Volume profile and trend analysis",
            params={"sma_period": 20},
        ),
        SkillDef(
            name="support_resistance",
            category=SkillCategory.TECHNICAL,
            description="Support and resistance level detection",
            params={"lookback": 50, "min_touches": 3},
        ),
        SkillDef(
            name="trend_analysis",
            category=SkillCategory.ANALYSIS,
            description="Trend direction and strength analysis",
            params={"method": "adx", "period": 14},
        ),
        SkillDef(
            name="volatility_analysis",
            category=SkillCategory.RISK,
            description="Market volatility estimation",
            params={"method": "atr", "period": 14},
        ),
        SkillDef(
            name="sentiment_score",
            category=SkillCategory.SENTIMENT,
            description="Market sentiment scoring from multiple sources",
            params={"sources": ["news", "social", "options"]},
        ),
        SkillDef(
            name="risk_calculator",
            category=SkillCategory.RISK,
            description="Position sizing and risk calculation",
            params={"max_risk_pct": 2.0, "method": "kelly"},
        ),
    ]

    for skill in skills:
        registry.register(skill)
