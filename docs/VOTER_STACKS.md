# Voter Stacks Map — Consolidation Prep (F3, observation only)

Five overlapping vote/decision stacks exist in `quant_nanggroe/engine/agentic/`.
All five are live-wired into `AutonomousPipeline` (`engine/agentic/autonomous.py`)
at different pipeline steps — i.e. a single signal currently passes through up
to FIVE successive votes before execution. No code changed here; F5-full decides.

## 1. SignalVotingSystem — `engine/agentic/voting.py:69`

- Entry: `SignalVotingSystem(config).vote(signals: list[Signal]) -> VoteResult`
  (`voting.py:89`). Inputs: bias/confidence/source triples with per-source
  weights + min-confidence/min-consensus thresholds. Outputs: `final_bias`,
  `weighted_confidence`, `consensus_strength`, dissenters (`voting.py:42-66`).
- Callers: `ensemble.py:39` (embedded inside EnsembleVoter); diagnostic API
  `api/routes/ensemble.py:46-48`; display-only `agentic/dashboard.py:36`.

## 2. EnsembleVoter — `engine/agentic/ensemble.py:29`

- Entry: `EnsembleVoter(config).run(symbol, primary_bias, primary_confidence,
  dataframe) -> (bias_str, confidence, metadata)` (`ensemble.py:43`).
  Inputs: primary strategy signal + OHLCV frame; fetches adapter signals via
  `adapters.fetch_all_signals` and delegates the count to stack #1.
  Outputs: voted bias + confidence + consensus metadata dict.
- Callers: pipeline Step 2.25 `autonomous.py:1002-1004` (always on unless
  `ensemble_voting_enabled=False`; overrides the signal only when consensus
  > 0.6). Thin wrapper over #1 — no independent vote math.

## 3. Council debate — `engine/agentic/council.py:117`

- Entry: `convene_council(symbol, proposed_signal, proposed_confidence, price,
  regime, council_size) -> CouncilDebateResult` (`council.py:117-124`).
  Inputs: ensemble output + optional price/regime. Persona agents lazy-loaded
  from `agents/personas/*` (`council.py:51-59`); score-weighted buy/sell/hold
  aggregation (`council.py:68-114`). Outputs: debated signal + confidence +
  per-persona votes + summary.
- Callers: pipeline Step 2.5 `autonomous.py:1024-1026` — ONLY when confidence
  < `DEBATE_THRESHOLD` (0.65); otherwise skipped. Referenced (docs string only)
  by `api/routes/debate.py:98`.

## 4. Committee VoteChamber — `engine/agentic/committee/vote_chamber.py:64`

- Entry: `VoteChamber().convene(symbol, df, **kwargs) -> CommitteeVote`
  (`vote_chamber.py:74`). Inputs: symbol + OHLCV + entry/ATR/regime/timeframe/
  lot/portfolio_state. Five specialist agents (`committee/agents.py`:
  Bull 35%/Bear 35%/Macro 30% weighted, RiskOfficer absolute veto,
  ExecutionAgent SL/TP). Outputs: `final_action` buy/sell/hold + confidence +
  consensus + `risk_vetoed` flag + SL/TP (`vote_chamber.py:26-41`).
- Callers: pipeline Step 2.6 `autonomous.py:1051-1072`. Only RiskAgent veto or
  a non-hold action with consensus > 0.1 overrides the signal; a committee
  HOLD preserves the ensemble signal (`autonomous.py:1074-1088`). This is the
  ONLY stack with a hard RiskAgent VETO and broker-truth portfolio wiring.

## 5. FinalDecider — `engine/agentic/final_decider.py:73`

- Entry: `FinalDecider(...).decide(signals, regime, portfolio, risk, atr,
  current_price) -> FinalDecision` (`final_decider.py:81`). Inputs: strategy
  signals + regime/ATR + portfolio caps + kill/drawdown/loss state. Proprietary
  veto chain (kill → drawdown → daily-loss → regime → confidence → exposure →
  positions → R:R ≥ 3.5) + Kelly sizing capped at 1% (`final_decider.py:84-123`).
  Outputs: action (strong_buy/buy/hold/sell/strong_sell) + Kelly fraction +
  position % + SL/TP + veto tags.
- Callers: pipeline Step 4 `autonomous.py:642` (init) + `autonomous.py:1208`
  (decide; skipped silently on exception, `autonomous.py:1219-1220`). Last
  gate before execution — can only narrow to HOLD, never originate a trade.

## Recommendation (F5-full)

Keep **#4 Committee VoteChamber** as the single surviving stack and fold the
others into it: it is the only voter with (a) an absolute RiskAgent veto, (b)
per-pair specialist roles (bull/bear/macro/risk/execution) instead of generic
weight averaging, and (c) live pipeline wiring that already consumes the
outputs of #2/#3 as its input signal (Steps 2.25→2.5→2.6 run in sequence, so
nothing upstream is lost). #1 is pure math with no callers outside #2 and the
diagnostic API — absorb its weighting into the chamber's consensus step; #2 is
a thin adapter-fan-in already feeding the chamber — keep the fan-in, drop the
class; #3's persona debate fires only on low confidence and never vetoes —
demote to an advisory note on the chamber vote; #5 duplicates constitutional
vetoes owned by the risk layer (kill/drawdown/daily-loss belong in
`engine/risk/`, not in a decider) — delete the veto chain, keep only its
Kelly+R:R sizing as a chamber post-step. Net: one vote per pair, one veto
owner (RiskAgent + risk layer), no silent skip paths.
