# Quant Nanggroe AI — Agent Instructions

## How AI Should Read This Repository
1. Start with `README.md` for project overview.
2. Read `00_VISION.md` and `01_PRD.md` for product context.
3. Read `02_ARCHITECTURE.md` for system structure.
4. Read `15_PROJECT_CONTEXT.md` for vocabulary and assumptions.
5. Read `16_AI_MEMORY.md` for stable facts and pitfalls.
6. Read `14_PROJECT_RULES.md` for governance rules.

## Order of Inspection
```
README.md → 00_VISION → 01_PRD → 02_ARCHITECTURE → 15_CONTEXT → 16_MEMORY
→ 04_API → 12_TASKS → 48_AUDIT → 17_GLOSSARY → 14_RULES
```

## What Not to Change Without Approval
- API contract (response envelope, endpoint paths).
- Risk engine logic (Kelly, VaR, drawdown limits).
- State file format in `paper_state/`.
- Agent registration in `daemon_manager.py`.

## How to Update Docs
- All doc changes in same PR as code changes.
- Follow `31_SELF_REVIEW.md` before finalizing.
- Use ADR format for architecture decisions (`11_DECISIONS.md`).
