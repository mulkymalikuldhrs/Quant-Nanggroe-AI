<!-- BANNER -->
<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a2e,50:2d2d44,100:3d3d5c&fontColor=94a3b8&descColor=64748b&height=220&section=header&text=Agentic%20AI%20System&fontSize=55&desc=Legacy+Multi-Agent+System+(Archived)&animation=fadeIn" />

<!-- TYPING SVG -->
<div align="center">
  <a href="https://git.io/typing-svg">
    <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&duration=3000&pause=1000&color=94A3B8&center=true&vCenter=true&width=600&lines=Archived+%7C+Legacy+Project;Python+%2B+Flask+Multi-Agent+System;Superseded+by+AI-MultiColony-Ecosystem;Preserved+for+Reference+Only" alt="Typing SVG" />
  </a>
</div>

<br/>

<!-- BADGES -->
<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Archived](https://img.shields.io/badge/Status-Archived-64748B?style=for-the-badge)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](./LICENSE)

</div>

---

## Overview

**Agentic AI System** is a **legacy, archived** multi-agent AI system built with Python and Flask. This was an earlier iteration of a multi-agent architecture that has since been superseded by the [AI-MultiColony-Ecosystem](https://github.com/mulkymalikuldhrs/AI-MultiColony-Ecosystem) project.

This repository is preserved for reference, historical context, and educational purposes. It is **no longer actively maintained**.

## Features (Historical)

### Multi-Agent Architecture
- Multiple specialized agents with distinct roles and capabilities
- Agent communication protocol for inter-agent messaging
- Task distribution and coordination engine
- Basic agent lifecycle management (spawn, execute, terminate)

### Flask API Server
- RESTful API for agent interaction and control
- WebSocket support for real-time agent communication
- Authentication and session management
- Admin dashboard for monitoring agent activity

### Agent Capabilities
- Configurable agent behaviors via JSON profiles
- Tool/function calling framework for agent actions
- Memory and context management per agent
- Basic planning and task decomposition

## Honest Notes

> **Before you explore this codebase:**

- **Archived/Legacy** — This project is archived and no longer maintained. It may contain outdated dependencies, known bugs, and architectural decisions that have been improved upon in later projects.
- **See AI-MultiColony-Ecosystem Instead** — The concepts and architecture from this project have been evolved and significantly improved in the [AI-MultiColony-Ecosystem](https://github.com/mulkymalikuldhrs/AI-MultiColony-Ecosystem). For active development, use that project instead.
- **Not Production Ready** — Even in its active period, this was a research prototype. Do not use this for production systems.
- **Dependencies May Be Outdated** — Python packages and Flask extensions referenced may have newer versions with breaking changes. Pin versions if you need to run this.
- **No Security Audits** — This code was never audited for security. Do not expose the Flask server to the internet.

## Quick Start (For Reference Only)

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
git clone https://github.com/mulkymalikuldhrs/Agentic-AI-System_OLD.git
cd Agentic-AI-System_OLD
pip install -r requirements.txt  # May require version pinning
```

### Running

```bash
python app.py
```

The Flask server will start at `http://localhost:5000`.

## Project Structure

```
Agentic-AI-System_OLD/
├── app.py               # Flask application entry point
├── agents/
│   ├── base.py          # Base agent class
│   ├── coordinator.py   # Agent coordination logic
│   ├── specialist/      # Specialized agent implementations
│   └── profiles/        # Agent configuration profiles
├── api/
│   ├── routes/          # API endpoint definitions
│   └── websocket.py     # WebSocket handler
├── core/
│   ├── memory/          # Agent memory management
│   ├── planning/        # Task planning engine
│   └── communication/   # Inter-agent messaging
├── config/              # Configuration files
└── tests/               # Test suites (may be incomplete)
```

## Migration Guide

If you're looking to build on the concepts from this project, here's how the architecture evolved:

| Agentic AI System (OLD) | AI-MultiColony-Ecosystem |
|--------------------------|--------------------------|
| Single Flask server | Modular microservices |
| Basic agent profiles | Colony-based agent ecosystems |
| Simple task queue | Advanced orchestration engine |
| In-memory agent state | Persistent state management |
| Basic WebSocket | Full real-time event system |

## Contributing

This project is **archived and not accepting contributions**. Please direct all efforts to the [AI-MultiColony-Ecosystem](https://github.com/mulkymalikuldhrs/AI-MultiColony-Ecosystem) instead.

## Disclaimer

This is archived legacy code preserved for reference. It is not maintained, may contain security vulnerabilities, and should not be used in production. For the current version of this concept, see [AI-MultiColony-Ecosystem](https://github.com/mulkymalikuldhrs/AI-MultiColony-Ecosystem).

## License

**MIT License** — see [LICENSE](./LICENSE) for details.

## Author

<div align="center">

**Mulky Malikul Dhaher**

[![GitHub](https://img.shields.io/badge/GitHub-mulkymalikuldhrs-181717?style=flat-square&logo=github)](https://github.com/mulkymalikuldhrs)
[![Email](https://img.shields.io/badge/Email-mulkymalikudhr@mail.com-EA4335?style=flat-square&logo=gmail&logoColor=white)](mailto:mulkymalikudhr@mail.com)

</div>

---

<!-- FOOTER BANNER -->
<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a2e,50:2d2d44,100:3d3d5c&fontColor=94a3b8&descColor=64748b&height=120&section=footer&text=&fontSize=0" />
