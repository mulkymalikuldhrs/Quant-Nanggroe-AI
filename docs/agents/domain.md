# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists — it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in. In multi-context repos, also check `src/<context>/docs/adr/` for context-scoped decisions.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

Single-context repo (this repo — most repos):

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

Multi-context repo (presence of `CONTEXT-MAP.md` at the root):

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← system-wide decisions
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← context-specific decisions
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_

---

## Repo-specific domain anchors

Until `CONTEXT.md` and `docs/adr/` exist, the canonical sources are:

- **`CANONICAL.md`** at the repo root — Single Source of Truth for the QNA system. Section 1 (Project Overview), Section 2 (Architecture Flow), Section 5 (Risk Management), Section 15 (File Inventory) are the closest substitutes for `CONTEXT.md`.
- **`AGENTS.md`** at the repo root — Hard-earned shortcuts: env quirks, exact commands, critical gotchas, the `## Key Modules` table, the skills inventory.
- **`docs/VECTOR_ARBITRAGE.md`** — domain knowledge for the vector arbitrage subsystem.
- **`docs/UI_PLAN_v8.0.22.md`** — dashboard design system and page inventory (31 pages).
- **`docs/SKILLS.md`** — full skill inventory (92 skills across 5 directories + 7 MCP).

If you're tempted to write `CONTEXT.md` from scratch, **don't** — it would duplicate `CANONICAL.md`. The domain-modeling skill will eventually extract the ubiquitous-language glossary from `CANONICAL.md` and write a thin `CONTEXT.md` that defers to it.

## Existing ADRs (informal)

This repo has no `docs/adr/` directory yet, but several decisions are documented in commit messages and CANONICAL §15.1–§15.10. Treat those as informal ADRs:

| "ADR" | Decision | Where |
|-------|----------|-------|
| 1 | MT5 as live broker (REAL-ONLY, no paper fallback) | `CANONICAL.md` §10 (Security) |
| 2 | Per-symbol risk config (perSymbol overrides) | `CANONICAL.md` §15.10 |
| 3 | One position per symbol (broker-truth enforcement) | `CANONICAL.md` §5.6 + `manager.py:execute_order` |
| 4 | Vector 6 modul live (observability, not execution gate) | `CANONICAL.md` §15.9 + `docs/VECTOR_ARBITRAGE.md` |
| 5 | RiskAgent VETO absolute (committee) | `CANONICAL.md` §5 |
| 6 | Hot-reload risk config (no daemon restart) | `engine/risk/constants.py:_reload_from_risk_config()` |
| 7 | Launch.bat single, WIB timezone | `launch.bat:1` + `CANONICAL.md` §1 |
| 8 | Per-symbol kill switch daily loss (-0.8% auto-expire) | `engine/risk/kill_switch.py` |
| 9 | 31 dashboard pages, high-end design system (Ethereal Glass + Asymmetrical Bento) | `dashboard/CLAUDE.md` |
| 10 | Graphify as knowledge substrate (28k nodes, 1219 communities) | `graphify-out/` + `CANONICAL.md` §1 |

When the `/domain-modeling` skill is invoked, these get extracted into proper `docs/adr/NNNN-*.md` files with the standard ADR template.
