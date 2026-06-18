# 📋 CHANGELOG - Autonomous Organism

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.0.0] - 2026-03-05 - PRODUCTION-READY RELEASE 🚀

### 🔥 Breaking Changes

- Replaced `gpt-5-nano` (non-existent model) with `gpt-4o-mini` as default AI model
- AI model now configurable via `VITE_AI_MODEL` environment variable
- `useOrganismSimulation.ts` deprecated in favor of `useOrganismReal.ts` for real Supabase data
- Agent modules converted from CommonJS to ESM (compatible with `"type": "module"`)

### ✨ New Features

- **Decision Engine Edge Function** (`run-decision`): Scores problems using sentiment analysis, automation potential, and money potential heuristics; optionally enhances with OpenAI API
- **Factory Engine Edge Function** (`run-factory`): Generates SaaS project templates from top idea candidates; optionally enhances with AI-generated landing pages
- **Growth Engine Edge Function** (`run-growth`): Generates marketing campaign ideas and simulates growth metrics; optionally enhances with AI content generation
- **Pipeline Status Panel**: Visual pipeline status in the dashboard showing Sense → Decision → Factory → Growth progress
- **Real Dashboard Metrics**: All metrics now pulled from actual Supabase queries (problem_raw, idea_candidates, engine_runs)
- **Engine Run Tracking**: All engine runs are tracked with status, timing, and metadata
- **Dynamic Engine Statuses**: Engine cards reflect real status (online/processing/error/idle) from engine_runs table
- **`.env.example`**: Comprehensive environment configuration template

### 🐛 Bug Fixes

- Fixed `gpt-5-nano` model reference that would fail at runtime (now uses configurable `gpt-4o-mini`)
- Fixed hardcoded absolute paths (`/home/mulky/...`) in factory/index.js, memory/index.js, and index.js — now uses `process.cwd()` relative paths
- Fixed `package.json` name from `vite_react_shadcn_ts` to `autonomous-organism`
- Fixed `package.json` version from `0.0.0` to `2.0.0`
- Fixed `index.html` title from "Lovable App" to "Autonomous Organism"
- Fixed `index.html` meta tags (description, author, og:title, twitter:site)
- Fixed ESLint configuration to ignore agent module directories and relax type rules
- Fixed agent modules using CommonJS (`require.main`, `module.exports`) in ESM context
- Fixed memory/index.js missing `path` import
- Fixed memory/index.js not creating directory before writing log file
- Fixed Index.tsx referencing hardcoded model strings instead of env var

### 🔄 Refactoring

- Converted all agent modules (decision, factory, sense, memory, immune, scheduler) to ESM syntax
- Replaced hardcoded dashboard metrics with real Supabase queries in `useOrganismReal.ts`
- Added `runFactory`, `runGrowth`, `runDecision` functions to `useOrganismReal.ts`
- Added engine runs, idea candidates, sources, and scheduler config queries to real data hooks
- Updated `Index.tsx` to use real data throughout (no more hardcoded numbers)
- Updated `OrganismCore` version references and footer

### 📄 Documentation

- Updated README.md to v2.0.0 with production-ready status
- Enhanced architecture diagram showing Edge Functions
- Added environment setup instructions
- Added trilingual disclaimer (EN/ID/CN) with contributor welcome and contact info
- Updated tech stack table with accurate versions

---

## [1.0.0] - 2026-03-04 - INITIAL RELEASE 🎉

### ✨ Features

- 🧠 Neural Core Engine with real-time state visualization
- 👁️ Sense Engine for environmental perception
- ⚡ Decision Engine for autonomous decision-making
- 🛡️ Immune System for self-healing and threat detection
- 💾 Memory System with persistent storage
- 🏭 Factory System for self-replication and evolution
- 📊 Scheduler for task scheduling and lifecycle management
- 🤖 AI Integration via Puter.js
- 📈 Real-time dashboard with animated visualizations
- 🔐 Authentication with Supabase Auth
- 🎨 Modern UI with shadcn/ui components

### 📄 Documentation

- Trilingual README (EN/ID/CN)
- CONTRIBUTING.md with education disclaimer
- CODE_OF_CONDUCT.md
- SECURITY.md with disclaimer
- MIT License (2026, Mulky Malikul Dhaher)

---

> **⚠️ For Education Purpose Only**
> This project is provided strictly for educational and research purposes. The authors and contributors assume **no responsibility or liability** for any damages, losses, or risks arising from the use of this software.
>
> **Contact:** Mulky Malikul Dhaher | mulkymalikudhr@mail.com
