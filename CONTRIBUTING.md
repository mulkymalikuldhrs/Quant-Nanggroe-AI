# Contributing to Quant Nanggroe AI

First of all, thank you for considering contributing to **Quant Nanggroe AI**! We appreciate the time and effort you are willing to invest in improving this project. This document provides a comprehensive set of guidelines for contributing to the repository. By participating in this project, you agree to abide by the terms outlined below.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
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

This project is committed to providing a welcoming and respectful experience for everyone. We expect all contributors to:

- Be respectful and constructive in all interactions
- Focus on what is best for the community and the project
- Show empathy toward other community members
- Gracefully accept constructive criticism
- Refrain from any form of harassment, discrimination, or personal attacks

Violations of these principles may result in removal from the project community.

---

## Getting Started

1. **Fork** the repository on GitHub: [https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Quant-Nanggroe-AI.git
   cd Quant-Nanggroe-AI
   ```
3. **Add the upstream remote** to keep your fork in sync:
   ```bash
   git remote add upstream https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI.git
   ```
4. **Install dependencies**:
   ```bash
   npm install
   ```
5. **Start the development server** to verify everything works:
   ```bash
   npm run dev
   ```

---

## How to Contribute

### Bug Fixes and Feature Development

1. **Check existing issues** to avoid duplicating work. If an issue does not exist, create one first.
2. **Create a feature branch** from `main`:
   ```bash
   git checkout main
   git pull upstream main
   git checkout -b feature/your-feature-name
   ```
   Use descriptive branch names:
   - `feature/add-ichimoku-indicator` for new features
   - `fix/backtest-slippage-calculation` for bug fixes
   - `docs/update-api-reference` for documentation changes
   - `refactor/pressure-engine-weights` for code refactoring
3. **Make your changes** following the coding standards below.
4. **Test your changes** thoroughly before submitting.
5. **Commit** with clear, descriptive messages.
6. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request** against the `main` branch of the upstream repository.

### Documentation Improvements

Documentation is just as important as code. If you find a typo, unclear explanation, or missing documentation, please submit a fix. Documentation contributions follow the same PR process as code contributions.

---

## Development Setup

### Prerequisites

- **Node.js** >= 18.0.0
- **npm** >= 9.0.0 (or yarn/pnpm)
- A modern code editor with TypeScript support (VS Code recommended)

### Optional API Keys (for full functionality)

- **Google Gemini API Key** — Required for LLM-powered agent swarm intelligence
- **Finnhub API Key** — For real-time market data feeds
- **AlphaVantage API Key** — For stock and forex technical indicators

### Build Commands

| Command | Description |
|---|---|
| `npm run dev` | Start the development server with hot module replacement |
| `npm run build` | Create an optimized production build |
| `npm run preview` | Preview the production build locally |
| `npx tsc --noEmit` | Run TypeScript type checking without emitting files |

---

## Coding Standards

### TypeScript

- All code must pass strict type checking (`strict: true` in `tsconfig.json`)
- Avoid the use of `any` type. Use `unknown` if the type is truly unknown and narrow it with type guards
- Use explicit return types for public functions and methods
- Prefer `interface` for object shapes and `type` for unions, intersections, and mapped types
- Use `readonly` modifiers for immutable data structures, especially in financial calculations

### React Components

- Use functional components with hooks (no class components)
- Follow the existing component naming convention: `PascalCase` for components, `camelCase` for utilities
- Each component should reside in its own file under `components/`
- All UI components must support both light and dark themes via the existing theme system
- Use the `WindowFrame` wrapper for any new window components to maintain the desktop OS experience

### Services and Engines

- Follow the existing service architecture pattern in `services/`
- Every new service must integrate with the `AuditLogger` for full traceability
- All financial calculations must be deterministic, testable, and free of floating-point precision issues where possible
- Sensor agents (Layer 2) must produce structured output types, never subjective analysis
- Any new data provider must be integrated through the `AutoSwitch` engine for failover support

### File Organization

- Keep components in `components/` and business logic in `services/`
- Type definitions shared across the project belong in `types.ts`
- Each service should have a single responsibility and a clear public API
- Documentation for services goes in `docs/`

---

## Commit Guidelines

We follow a structured commit message format to maintain a clean and readable git history:

```
type(scope): description

[optional body]

[optional footer]
```

### Types

| Type | Description |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation changes |
| `style` | Code style changes (formatting, no logic change) |
| `refactor` | Code refactoring (no feature or fix) |
| `test` | Adding or updating tests |
| `chore` | Build process, dependencies, or tooling changes |

### Scopes

Common scopes include: `engine`, `agent`, `ui`, `market`, `risk`, `backtest`, `audit`, `config`

### Examples

```
feat(agent): add Ichimoku Cloud indicator to MathEngine
fix(backtest): correct slippage calculation for high-volatility regimes
docs(api): update MarketService API reference with new endpoints
refactor(pressure): simplify weight calculation in PressureNormalizationEngine
```

---

## Pull Request Process

1. **Ensure your branch is up to date** with `main`:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
2. **Verify your changes** pass TypeScript type checking:
   ```bash
   npx tsc --noEmit
   ```
3. **Write a clear PR description** that includes:
   - What changes were made and why
   - Which issue(s) the PR addresses (if applicable)
   - Any breaking changes or migration steps
   - Screenshots or recordings for UI changes
4. **Keep PRs focused** — one feature or fix per PR. Large, multi-feature PRs are harder to review and may be asked to be split.
5. **Respond to code review feedback** promptly and constructively.
6. **Do not force-push** to your PR branch after review has started, unless specifically requested.

### PR Review Criteria

A PR will be merged when it:
- Passes TypeScript strict type checking
- Follows the coding standards outlined in this document
- Includes appropriate audit logging for new services
- Does not introduce regressions in existing functionality
- Has clear, descriptive commit messages
- Is approved by at least one maintainer

---

## Reporting Issues

When reporting bugs or requesting features, please use the GitHub Issues page and include:

### Bug Reports

- **Summary**: A clear, concise description of the bug
- **Steps to Reproduce**: Numbered steps that reliably trigger the issue
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: Browser, Node.js version, OS
- **Screenshots/Logs**: If applicable, attach screenshots or console output

### Feature Requests

- **Problem Statement**: What problem does this feature solve?
- **Proposed Solution**: How should the feature work?
- **Alternatives Considered**: What other approaches have you considered?
- **Additional Context**: Any relevant links, references, or mockups

---

## Areas of Contribution

We are actively seeking contributions in the following areas:

### High Priority

- **Testing** — Unit tests, integration tests, and end-to-end testing for all engines and services. The project currently lacks comprehensive test coverage, and this is our most critical need.
- **Indicators** — Additional technical indicators for the MathEngine, including Ichimoku Cloud, Fibonacci retracements and extensions, Elliott Wave pattern detection, and Volume-Weighted Average Price (VWAP) improvements.

### Medium Priority

- **Data Providers** — New API integrations to expand market data coverage, including Yahoo Finance, CoinGecko, TradingView WebSocket feeds, and other institutional data sources.
- **UI/UX** — Component improvements, accessibility enhancements (ARIA compliance), mobile responsiveness, and new visualization components for agent activity and market data.

### Ongoing Needs

- **Documentation** — API documentation, step-by-step tutorials, architecture deep-dives, and example configurations for common trading scenarios.
- **Internationalization** — Translations of the UI and documentation into additional languages. We currently support English, Bahasa Indonesia, and Chinese, and welcome contributions in any language.
- **Cloud Deployment** — Docker containerization, Kubernetes orchestration, CI/CD pipeline configuration, and cloud-native deployment guides.

---

## License

By contributing to Quant Nanggroe AI, you agree that your contributions will be licensed under the **MIT License**, the same license that covers the project. This means that your code will be freely available for others to use, modify, and distribute under the terms of the MIT License.

---

## Contact

For questions, suggestions, or collaboration inquiries:

- **Owner**: Mulky Malikul Dhaher
- **Email**: [mulkymalikuldhaher@email.com](mailto:mulkymalikuldhaher@email.com)
- **GitHub**: [https://github.com/mulkymalikuldhrs](https://github.com/mulkymalikuldhrs)
- **Repository**: [https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)

> Part of the [HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) Unified Project.

---

Thank you for contributing to Quant Nanggroe AI. Your efforts help build a more transparent, deterministic, and intelligent future for quantitative trading.
