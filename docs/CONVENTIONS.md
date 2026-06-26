# Quant-Nanggroe-AI Coding Conventions

## General Principles

1. **Deterministic First** — All engine code must be 100% deterministic. No AI, no randomness, no approximation in the math/engine layer.
2. **Type Safety** — Every function must have type hints. Use Pydantic models for all data validation.
3. **Constitutional Immutability** — Risk limits (0.5%/trade, 1%/day, 3%/week) are hardcoded constants. No override possible.
4. **Audit Everything** — Every decision must be traceable. Use the AuditLogger for all decision-layer events.
5. **Fail-Safe Defaults** — When in doubt, default to NO_TRADE. Kill switch must auto-activate on breach.

## Python Style

- **Python 3.12+** with full type annotations
- **Ruff** for formatting and linting (line length: 100)
- **Pydantic v2** for all data models and settings
- **async/await** for all I/O-bound operations
- **Structured logging** via `structlog`
- **No `Any` type** — use proper types or `object`

## Module Organization

```
src/quant_nanggroe_ai/
├── engine/     # Deterministic — no AI, no external calls
├── agents/     # AI agents — LangGraph / CrewAI
├── data/       # Data connectors and models
├── risk/       # Risk calculations (VaR, CVaR, etc.)
├── execution/  # Order execution
├── backtest/   # Backtesting engine
├── factors/    # Alpha factors
├── memory/     # Knowledge and memory
└── api/        # FastAPI endpoints
```

## Naming Conventions

- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`
- **Pydantic models**: Suffix with `Schema`, `Request`, `Response`, or `Model`

## Engine Layer Rules

- NO external API calls
- NO LLM/AI inference
- NO randomness (use deterministic seeds if needed for Monte Carlo)
- ALL functions must be independently testable
- Return typed dicts or Pydantic models, never raw JSON strings

## Agent Layer Rules

- Use LangGraph for state machines
- Each agent is a node in the graph
- Agents communicate through shared `AgentState`
- Risk Manager has VETO authority
- Portfolio Manager is the final gate

## Risk Rules (NON-NEGOTIABLE)

```python
MAX_RISK_PER_TRADE = 0.005   # 0.5% — HARDCODED
MAX_DAILY_LOSS = 0.01        # 1.0% — HARDCODED
MAX_WEEKLY_LOSS = 0.03       # 3.0% — HARDCODED
MIN_RISK_REWARD = 2.0        # 1:2 minimum — HARDCODED
```

## Git Conventions

- **Branch naming**: `feat/`, `fix/`, `refactor/`, `docs/`, `test/`
- **Commit format**: Conventional Commits (`feat:`, `fix:`, `chore:`, etc.)
- **PR size**: Max 400 lines changed per PR
- **Pre-commit hooks**: Must pass before merge

## Testing Requirements

- All engine modules must have corresponding test files
- Minimum 80% coverage for engine layer
- Use `pytest` with `pytest-asyncio`
- Mark tests with appropriate markers: `@pytest.mark.engine`, `@pytest.mark.agents`, etc.
