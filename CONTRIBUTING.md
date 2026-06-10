# Contributing to Quant Nanggroe AI

Terima kasih atas minat Anda untuk berkontribusi ke **Quant Nanggroe AI**! Dokumen ini menyediakan panduan komprehensif untuk berkontribusi ke monorepo ini.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Monorepo Structure](#monorepo-structure)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [Areas of Contribution](#areas-of-contribution)
- [License](#license)

---

## Code of Conduct

Kami berkomitmen untuk menyediakan pengalaman yang ramah dan hormat untuk semua kontributor. Harap:

- Bersikap hormat dan konstruktif dalam semua interaksi
- Fokus pada apa yang terbaik untuk komunitas dan proyek
- Menunjukkan empati terhadap anggota komunitas lainnya
- Menerima kritik konstruktif dengan anggun
- Menahan diri dari segala bentuk pelecehan, diskriminasi, atau serangan pribadi

---

## Monorepo Structure

Quant Nanggroe AI adalah **monorepo** yang mengkonsolidasikan 25+ repositori ke dalam satu kodebase terpadu:

```
Quant-Nanggroe-AI/
├── src/quant_nanggroe_ai/       # Python backend (21 packages)
│   ├── agents/                  # 9-node LangGraph agent system
│   ├── api/                     # FastAPI server + JWT auth
│   ├── backtest/                # 9 backtest engines + NautilusTrader
│   ├── data/                    # Database + Cache (PostgreSQL, Redis)
│   ├── engine/                  # Deterministic engine layer
│   ├── execution/               # 5 execution brokers
│   ├── factors/                 # 456+ alpha factors
│   ├── hedge_fund/              # AI Hedge Fund subsystem
│   ├── integrations/            # WhatsApp bot + external integrations
│   ├── memory/                  # Vector + conversation + research
│   ├── ml_models/               # Kronos model + finetune
│   ├── risk/                    # VaR, CVaR, drawdown, position sizing
│   ├── solana_scanner/          # Solana on-chain scanner
│   └── tools/                   # 22 engine tools
├── components/                  # React 19 UI (25 components)
├── services/                    # TypeScript services (33 files)
├── tests/                       # 30+ test files (175+ tests)
├── alembic/                     # Database migrations
├── docs/                        # Documentation
├── repos/                       # 59 cloned source repos (reference only)
└── scripts/                     # Dev setup scripts
```

### Key Packages

| Package | Fungsi | Status |
|---------|--------|--------|
| `agents/` | LangGraph agent system, 9 nodes, MCP/A2A | ✅ Production |
| `api/` | FastAPI + JWT auth, 6 routers | ✅ Production |
| `backtest/` | 9 engines, 4 optimizers, 8 loaders | ✅ Production |
| `engine/` | Deterministic engine (no AI) | ✅ Production |
| `execution/` | 5 brokers (paper, alpaca, jupiter, polymarket, kalshi) | ✅ Production |
| `factors/` | 456+ alpha factors | ✅ Production |
| `risk/` | VaR, CVaR, drawdown, sizing | ✅ Production |
| `hedge_fund/` | AI hedge fund agents | ⚠️ Partial |
| `integrations/` | WhatsApp + Trading Plan | ✅ New |
| `solana_scanner/` | Solana scanner | ⚠️ Partial |

---

## Getting Started

### 1. Fork dan Clone

```bash
git clone https://github.com/YOUR_USERNAME/Quant-Nanggroe-AI.git
cd Quant-Nanggroe-AI
git checkout Julecl1
```

### 2. Add Upstream

```bash
git remote add upstream https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI.git
```

### 3. Install Dependencies

```bash
# Python backend
poetry install

# Node.js frontend
npm install
```

### 4. Verify Setup

```bash
# Run tests
poetry run pytest

# Check import integrity
PYTHONPATH=src python -c "import quant_nanggroe_ai; print('OK')"

# Start dev server
poetry run uvicorn quant_nanggroe_ai.main:app --reload
```

---

## How to Contribute

### Bug Fixes and Feature Development

1. **Check existing issues** untuk menghindari duplikasi
2. **Create a feature branch** dari `Julecl1`:
   ```bash
   git checkout Julecl1
   git pull upstream Julecl1
   git checkout -b feature/your-feature-name
   ```
3. **Gunakan descriptive branch names:**
   - `feature/add-kalshi-broker` untuk fitur baru
   - `fix/backtest-slippage-calculation` untuk bug fix
   - `docs/update-api-reference` untuk dokumentasi
   - `refactor/pressure-engine-weights` untuk refactoring
4. **Make your changes** mengikuti coding standards
5. **Test your changes** sebelum submit
6. **Commit** dengan pesan yang jelas
7. **Push** ke fork Anda:
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Open a Pull Request** terhadap `Julecl1` branch

---

## Development Setup

### Prerequisites

| Stack | Requirement |
|-------|-------------|
| **Python Backend** | Python >= 3.12, Poetry >= 1.8 |
| **Node.js Frontend** | Node.js >= 18.0.0, npm >= 9.0.0 |
| **Database** | PostgreSQL 16+, Redis 7+ |
| **Optional** | QuestDB (time-series), Docker |

### Build Commands

| Command | Description |
|---------|-------------|
| `poetry install` | Install Python dependencies |
| `poetry run pytest` | Run all tests |
| `poetry run pytest --cov` | Run tests with coverage |
| `poetry run uvicorn quant_nanggroe_ai.main:app --reload` | Start FastAPI dev server |
| `npm run dev` | Start frontend dev server |
| `npm run build` | Build frontend for production |
| `docker-compose up -d` | Start all services |
| `poetry run alembic upgrade head` | Run database migrations |
| `poetry run ruff check src/` | Lint Python code |
| `poetry run mypy src/` | Type check Python code |

### Environment Variables

Copy `.env.example` ke `.env` dan isi:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `ALPACA_API_KEY` | No | Alpaca broker |
| `SOLANA_PRIVATE_KEY` | No | Jupiter/Solana broker |
| `POLYMARKET_API_KEY` | No | Polymarket broker |
| `KALSHI_API_KEY` | No | Kalshi broker |

---

## Coding Standards

### Python

- **Python 3.12+** dengan type annotations lengkap
- **Ruff** untuk formatting dan linting (line length: 100)
- **Pydantic v2** untuk semua data models dan settings
- **async/await** untuk semua I/O-bound operations
- **No `Any` type** — gunakan proper types atau `object`
- **Structured logging** via `structlog`

### Import Rules (KRITIS)

> **ATURAN PENTING:** Semua import harus menggunakan package path `quant_nanggroe_ai.*`, BUKAN `src.*`

```python
# ✅ CORRECT
from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard
from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool

# ❌ WRONG (will break at runtime)
from src.engine.risk_guard import ConstitutionalRiskGuard
from src.agents.tools.market_data import MarketDataTool
```

### Module Organization

```
src/quant_nanggroe_ai/
├── engine/     # Deterministic — no AI, no external calls
├── agents/     # AI agents — LangGraph / CrewAI / PydanticAI / DSPy
├── data/       # Data connectors and models
├── risk/       # Risk calculations (VaR, CVaR, etc.)
├── execution/  # Order execution brokers
├── backtest/   # Backtesting engine
├── factors/    # Alpha factors
├── memory/     # Knowledge and memory
├── api/        # FastAPI endpoints
└── integrations/ # External integrations
```

### Engine Layer Rules (NON-NEGOTIABLE)

- **NO** external API calls
- **NO** LLM/AI inference
- **NO** randomness (use deterministic seeds jika diperlukan)
- **ALL** functions must be independently testable
- Return typed dicts atau Pydantic models, **NEVER** raw JSON strings

### Agent Layer Rules

- Gunakan LangGraph untuk state machines
- Setiap agent adalah node dalam graph
- Agent berkomunikasi melalui shared `AgentState`
- Risk Manager memiliki **VETO** authority
- Portfolio Manager adalah **final gate**

### React Components

- Functional components with hooks (no class components)
- PascalCase untuk components, camelCase untuk utilities
- Setiap component dalam file sendiri di `components/`
- Semua UI components harus mendukung light dan dark themes
- Gunakan `WindowFrame` wrapper untuk window components baru

### TypeScript Services

- Follow existing service architecture pattern di `services/`
- Setiap service harus integrate dengan audit logging
- Gunakan typed interfaces untuk semua data structures

---

## Commit Guidelines

Kami mengikuti format Conventional Commits:

```
type(scope): description

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | Fitur baru |
| `fix` | Bug fix |
| `docs` | Perubahan dokumentasi |
| `style` | Perubahan format (tanpa logic change) |
| `refactor` | Refactoring (tanpa fitur atau fix) |
| `test` | Menambah atau update test |
| `chore` | Build, dependencies, atau tooling |

### Scopes

Common scopes: `engine`, `agents`, `api`, `execution`, `factors`, `backtest`, `risk`, `memory`, `ui`, `market`, `solana`, `integrations`, `docs`

### Examples

```
feat(execution): add Kalshi broker with RSA-PSS authentication
fix(factors): correct alpha020 missing low parameter
docs(api): update FastAPI route documentation
refactor(agents): simplify LangGraph conditional routing
test(risk): add Monte Carlo VaR test cases
chore(deps): add cryptography>=41.0.0 for Kalshi broker
```

---

## Pull Request Process

1. **Ensure branch is up to date** dengan `Julecl1`:
   ```bash
   git fetch upstream
   git rebase upstream/Julecl1
   ```
2. **Verify changes:**
   ```bash
   # Python type check
   poetry run mypy src/
   # Python lint
   poetry run ruff check src/
   # Run tests
   poetry run pytest
   # Import verification
   PYTHONPATH=src python -c "import quant_nanggroe_ai"
   ```
3. **Write a clear PR description** yang mencakup:
   - Perubahan apa dan mengapa
   - Issue yang di-address (jika ada)
   - Breaking changes atau migration steps
   - Screenshots untuk UI changes
4. **Keep PRs focused** — satu fitur atau fix per PR
5. **Respond to review feedback** dengan segera dan konstruktif
6. **Do not force-push** setelah review dimulai

### PR Review Criteria

PR akan di-merge ketika:
- Passes Python type checking dan linting
- Passes semua existing tests
- Follows coding standards di dokumen ini
- Includes appropriate test coverage untuk kode baru
- Has clear, descriptive commit messages
- Is approved by at least one maintainer

---

## Reporting Issues

### Bug Reports

- **Summary**: Deskripsi jelas dan ringkas
- **Steps to Reproduce**: Langkah-langkah yang reliably trigger issue
- **Expected Behavior**: Apa yang diharapkan
- **Actual Behavior**: Apa yang sebenarnya terjadi
- **Environment**: Python version, OS, database
- **Logs/Screenshots**: Jika berlaku

### Feature Requests

- **Problem Statement**: Masalah apa yang dipecahkan fitur ini?
- **Proposed Solution**: Bagaimana fitur ini seharusnya bekerja?
- **Alternatives Considered**: Pendekatan lain yang dipertimbangkan
- **Additional Context**: Link, referensi, atau mockups

---

## Areas of Contribution

### 🔴 High Priority

- **Test Coverage** — Unit tests, integration tests untuk execution brokers, hedge_fund, memory, solana_scanner
- **Frontend-Backend Integration** — TypeScript API client untuk FastAPI backend
- **Authentication Wiring** — Connect JWT middleware ke semua API routes

### 🟠 Medium Priority

- **fincept_terminal Stubs** — Implement atau remove ~50 NotImplementedError stubs
- **CI Pipeline** — GitHub Actions config untuk automated testing dan deployment
- **Rate Limiting** — API rate limiting middleware
- **Data Providers** — Yahoo Finance, CoinGecko, TradingView WebSocket integrations

### 🟡 Ongoing Needs

- **Documentation** — API docs, tutorials, architecture deep-dives
- **Internationalization** — UI dan docs translations (saat ini EN, ID, CN)
- **Monitoring** — Prometheus metrics, OpenTelemetry tracing
- **New Factors** — Additional alpha factors untuk factor library
- **New Brokers** — Interactive Brokers, Binance, OKX direct integrations

---

## License

Dengan berkontribusi ke Quant Nanggroe AI, Anda menyetujui bahwa kontribusi Anda akan dilisensikan di bawah **MIT License**.

---

## Contact

- **Owner**: Mulky Malikul Dhaher
- **Email**: [mulkymalikuldhaher@email.com](mailto:mulkymalikuldhaher@email.com)
- **GitHub**: [https://github.com/mulkymalikuldhrs](https://github.com/mulkymalikuldhrs)
- **Repository**: [https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)

> Bagian dari [HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) Unified Project.

---

> ⚠️ **For Education Purpose Only** — Proyek ini disediakan secara ketat untuk tujuan pendidikan dan penelitian. Penulis dan kontributor tidak menanggung tanggung jawab atas kerugian atau risiko yang timbul dari penggunaan perangkat lunak ini.
