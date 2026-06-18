<div align="center">

<!-- 动画：打字标题 -->
<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=36&duration=3000&pause=1000&color=00FF88&center=true&vCenter=true&multiline=true&repeat=true&width=800&height=120&lines=HERMES+QUANT+OS;自主多代理交易基础设施" alt="HERMES QUANT OS" />

<br/>

<!-- 动画徽章 -->
<img src="https://img.shields.io/badge/版本-4.0.0-00FF88?style=for-the-badge&logo=semver&logoColor=white&labelColor=0A0A0A" alt="版本" />
<img src="https://img.shields.io/badge/阶段-Alpha_开发中-FFA500?style=for-the-badge&logo=semver&logoColor=white&labelColor=0A0A0A" alt="阶段" />
<img src="https://img.shields.io/badge/代理-21个_5层架构-FF6B35?style=for-the-badge&logo=azuredevops&logoColor=white&labelColor=0A0A0A" alt="代理" />
<img src="https://img.shields.io/badge/许可证-MIT-blue?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=0A0A0A" alt="许可证" />

<br/><br/>

<!-- 语言切换 -->
<a href="./README.md"><img src="https://img.shields.io/badge/EN-English-00D4FF?style=flat-square" /></a>
<a href="./README_id.md"><img src="https://img.shields.io/badge/ID-Bahasa_Indonesia-FF6B35?style=flat-square" /></a>
<a href="./README_zh.md"><img src="https://img.shields.io/badge/CN-中文-00FF88?style=flat-square" /></a>

<br/><br/>

<!-- 动画：脉冲 -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0A0A0A,50:1A1A2E,100:16213E&height=120&section=header&text=&fontSize=0&animation=fadeIn" width="100%" alt="Header Wave" />

<br/>

**基于 [NousResearch/Hermes](https://github.com/NousResearch/Hermes)** ⭐ **的 Fork**
**融合 [Quant-Nanggroe-AI](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI) | [AI-MultiColony-Ecosystem](https://github.com/mulkymalikuldhrs/AI-MultiColony-Ecosystem) | [Vibe-Trading](https://github.com/mulkymalikuldhrs/Vibe-Trading) | [AutoHedge](https://github.com/mulkymalikuldhrs/AutoHedge)**

<br/>

<em>"不仅仅是一个助手。一个守护方向、质量和资本效率的自主交易系统。"</em>

</div>

---

## 目录

- [概述](#概述)
- [起源与Fork谱系](#起源与fork谱系)
- [架构：21个代理，5个层级](#架构21个代理5个层级)
- [风险架构（宪政守护）](#风险架构宪政守护)
- [自动重启基础设施](#自动重启基础设施)
- [快速开始](#快速开始)
- [命令](#命令)
- [工具系统](#工具系统)
- [配置](#配置)
- [部署阶段](#部署阶段)
- [项目结构](#项目结构)
- [版本历史](#版本历史)
- [路线图](#路线图)
- [贡献](#贡献)
- [联系方式](#联系方式)
- [许可证](#许可证)

---

## 概述

<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=18&duration=4000&pause=1000&color=00FF88&center=true&vCenter=true&repeat=true&width=700&height=40&lines=Jarvis级自主交易系统;SaaS+本地部署生产就绪" alt="打字" />
</div>

Hermes Quant Operating System 是一个**生产级自主多代理交易和研究基础设施**，旨在实现持续资本增长和绝对风险保全。系统运行遵循一个原则：交易决策必须是**确定性的、基于数据的，并受制于任何代理都无法绕过的风险约束**——包括LLM本身。

该架构将四个参考仓库中最强的模式综合成一个统一的交易系统，建立在Nous Research Hermes Agent框架之上：

| 来源仓库 | 贡献 | 版本 |
|---|---|---|
| **[NousResearch/Hermes](https://github.com/NousResearch/Hermes)** ⭐ | 基础代理框架、工具编排、对话循环 | 上游 |
| **[Quant-Nanggroe-AI](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)** | 确定性代理执行、压力归一化、市场状态引擎、达尔文策略进化、10个集成工具 | v15.2.0 |
| **[AI-MultiColony-Ecosystem](https://github.com/mulkymalikuldhrs/AI-MultiColony-Ecosystem)** | 统一代理注册、多代理生命周期管理、集群协调 | v8.0.0 |
| **[Vibe-Trading](https://github.com/mulkymalikuldhrs/Vibe-Trading)** | 450+预构建量化因子、因子纯度执行、因子分析 | v0.1.8 |
| **[AutoHedge](https://github.com/mulkymalikuldhrs/AutoHedge)** | 集群管道架构（Director → Quant → Risk → Execution）、特定场所集成 | 最新 |

### 核心能力

- **21个专业化代理**分布于5个架构层（数据 → 分析 → 决策 → 执行 → 学习）
- **宪政风险守护**，采用硬编码限制，任何代理（包括LLM）都无法绕过
- **3层自动重启基础设施**，增强系统可靠性（Watchdog + Keeper + 开机启动）
- **多提供商LLM**，自动故障转移（NVIDIA Nemotron 70B → Groq Llama → OpenCode）
- **SQLite持久化**，用于交易状态、PnL、终止开关事件和策略生命周期
- **Telegram Bot接口**，用于实时命令、交易信号和系统警报
- **跨平台**部署：Android（Termux）、Linux（systemd）、VPS或本地机器
- **完整审计追踪**，从传感器数据到最终交易决策

---

## 起源与Fork谱系

```
[NousResearch/Hermes](https://github.com/NousResearch/Hermes) (原始Hermes模型和代理)
        │
        │  Fork 与适配
        ▼
┌───────────────────────────────────────────────────┐
│        HERMES QUANT OPERATING SYSTEM               │
│        (HermesQuantOS)                             │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │  Nous Research Hermes (基础框架)             │  │
│  │  - 代理循环架构                              │  │
│  │  - 工具编排系统                              │  │
│  │  - 对话管理                                  │  │
│  └─────────────────────────────────────────────┘  │
│        │          │          │          │          │
│        ▼          ▼          ▼          ▼          │
│  ┌──────────┐┌──────────┐┌──────────┐┌────────┐  │
│  │Quant-    ││AI-Multi  ││Vibe-     ││Auto-   │  │
│  │Nanggroe  ││Colony-   ││Trading   ││Hedge   │  │
│  │-AI       ││Ecosystem ││          ││        │  │
│  │          ││          ││          ││        │  │
│  │压力引擎  ││代理注册  ││Alpha动物园││集群管线│  │
│  │决策引擎  ││生命周期  ││(450+     ││主管    │  │
│  │市场状态  ││集群协调  ││因子)     ││量化    │  │
│  │新闻哨兵  ││          ││因子分析  ││风控    │  │
│  │策略生命周期││         ││回测框架  ││执行    │  │
│  │数学引擎  ││          ││          ││        │  │
│  │SMC增强版 ││          ││          ││        │  │
│  │回测引擎  ││          ││          ││        │  │
│  │审计日志  ││          ││          ││        │  │
│  └──────────┘└──────────┘└──────────┘└────────┘  │
│                                                    │
│  + AGENTS.md 宪政框架                              │
│  + 3层自动重启基础设施                             │
│  + SQLite持久化与共享状态                           │
│  + 多提供商LLM故障转移                             │
└───────────────────────────────────────────────────┘
```

---

## 架构：21个代理，5个层级

<div align="center">

| 层级 | 代理 | 目的 |
|:---:|:---:|:---:|
| **L1** 数据 | Market Data, Chart Vision | 数据摄取与视觉分析 |
| **L2** 分析 | Technical, Macro/Sentiment, SMC Enhanced, News Sentinel, Market State | 市场分析与状态检测 |
| **L3** 决策 | Strategy, Risk Officer (VETO), Portfolio, Decision Engine, Pressure Engine, Strategy Lifecycle | 决策综合与风险门控 |
| **L4** 执行 | Execution, Kill Switch, Auto-Switch Engine | 交易执行与紧急控制 |
| **L5** 学习 | Journal, Auditor, Research, Audit Logger, Backtest, Math Engine | 自我改进与验证 |

</div>

### 数据流管道

```
市场数据 (L1)  ──→  分析 (L2)  ──→  压力归一化  ──→  决策 (L3)
                                                                   │
                                                              风险官
                                                            9检查关卡
                                                                   │
                                                         VETO → 阻止（不可覆盖）
                                                         APPROVE → 执行 (L4)
                                                                   │
                                                              学习 (L5)
                                                                   │
                                                         自我改进循环
```

---

## 风险架构（宪政守护）

<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=16&duration=3000&pause=2000&color=FF4444&center=true&vCenter=true&repeat=true&width=600&height=35&lines=0.5%25+每笔交易+%7C+1%25+每日+%7C+3%25+每周;硬编码+%E2%80%94+不可覆盖" alt="风险规则" />
</div>

风险系统在架构上**独立于**LLM推理层。风险决策由**具有硬编码常量的确定性Python代码**做出，而非LLM。这防止了任何形式的"绕过"安全规则的推理。

### 风险规则（不可变常量）

```python
RISK_MAX_PER_TRADE = 0.005     # 0.5% — 不可覆盖
RISK_DAILY_MAX     = 0.01     # 1.0% — 不可覆盖
RISK_WEEKLY_MAX    = 0.03     # 3.0% — 不可覆盖
```

这些是Python模块级常量。它们**不**从配置文件加载，**不**存储在环境变量中，**不**作为函数参数传递。要更改它们需要直接编辑源代码，这将被PR审查捕获。

### 风险官9检查关卡

每笔交易必须通过所有9个检查点。风险官拥有**完全否决权**——如果任何检查点失败，交易将被拒绝，**没有任何代理可以覆盖此决定**。

| # | 检查点 | 规则 |
|---|---|---|
| 1 | 账户余额 | 余额充足以开仓 |
| 2 | 每日亏损限制 | 当前每日PnL在1%以内 |
| 3 | 每周亏损限制 | 当前每周PnL在3%以内 |
| 4 | 仓位大小 | 每笔交易风险在0.5%以内 |
| 5 | 风险报酬比 | 最低1:2 |
| 6 | 止损存在 | 强制性，无例外 |
| 7 | 汇合评分 | 最低3/5 |
| 8 | 市场状态 | 与当前状态兼容 |
| 9 | 相关性检查 | 活跃头寸相关性 < 0.70（计划中） |

### 终止开关

- 当每日/每周限制被突破时自动激活
- 仅在审查后手动重置
- 任何代理都无法覆盖，包括所有者

---

## 自动重启基础设施

```
┌─────────────────────────────────────────┐
│  第3层：开机启动                         │
│  Termux:Boot / systemd / cron @reboot   │
│  → 启动时运行 hermes.sh start           │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  第2层：KEEPER（Cron，1分钟间隔）        │
│  健康检查 → 如果都死亡则重启            │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  第1层：WATCHDOG（10秒间隔）             │
│  监控 → 指数退避重启                    │
│  5s → 10s → 20s → 40s → 80s → 120s    │
│  崩溃循环：最多10次/小时 → 5分钟冷却    │
│  每个事件的Telegram警报                 │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  HERMES QUANT OS（主进程）               │
│  21个工具 | 多提供商LLM | SQLite        │
└─────────────────────────────────────────┘
```

---

## 快速开始

### Android (Termux)

```bash
chmod +x scripts/install_termux.sh
./scripts/install_termux.sh
```

### Linux 服务器

```bash
chmod +x scripts/install_server.sh
sudo ./scripts/install_server.sh
```

### 手动启动

```bash
# 克隆仓库
git clone https://github.com/mulkymalikuldhrs/HermesQuantOS.git
cd HermesQuantOS

# 安装依赖
pip install -r requirements.txt

# 配置环境
cp config/.env.example config/.env
# 使用您的API密钥编辑 config/.env

# 使用watchdog启动（自动重启）
bash hermes.sh start
```

---

## 命令

```bash
bash hermes.sh start      # 使用watchdog启动（自动重启）
bash hermes.sh stop       # 优雅停止所有进程
bash hermes.sh restart    # 重启Hermes + Watchdog
bash hermes.sh status     # 系统健康与PnL状态
bash hermes.sh logs       # 查看最新日志
bash hermes.sh health     # 详细健康检查
bash hermes.sh install    # 安装开机启动 + 自动重启
```

### Telegram Bot 命令

| 命令 | 描述 |
|---|---|
| `/start` | 欢迎消息与系统概览 |
| `/status` | 系统健康、运行时间、PnL |
| `/market [代码]` | OHLCV数据（XAUUSD、EURUSD等） |
| `/analyze [代码]` | SMC技术分析 |
| `/risk` | 风险官状态 |
| `/strategy [代码]` | 3场景分析 |
| `/journal` | 交易日志统计 |
| `/kill` | 终止开关状态 |
| `/pnl` | PnL报告 |
| `/help` | 完整帮助菜单 |

---

## 工具系统

### L1：数据层

| 工具 | 文件 | 描述 |
|---|---|---|
| `market_data` | `src/tools/market_data_tool.py` | 通过yfinance/MT5/OANDA/Binance获取OHLCV数据 |
| `chart_vision` | `src/tools/chart_vision_tool.py` | 通过视觉LLM进行图表图像分析 |

### L2：分析层

| 工具 | 文件 | 描述 |
|---|---|---|
| `technical_analysis` | `src/tools/technical_analysis_tool.py` | SMC结构检测（BOS/CHoCH/OB/FVG/Sweeps） |
| `macro_sentiment` | `src/tools/macro_sentiment_tool.py` | 风险开/关状态检测、情绪分析 |
| `smc_enhanced` | `src/tools/smc_agent_enhanced.py` | 增强版SMC，包含订单块、FVG、流动性扫荡 |
| `news_sentinel` | `src/tools/news_sentinel.py` | 带对数时间衰减的宏观影响评分 |
| `market_state` | `src/tools/market_state_engine.py` | 市场状态引擎（趋势/区间/避险/恐慌/不交易） |

### L3：决策层

| 工具 | 文件 | 描述 |
|---|---|---|
| `strategy` | `src/tools/strategy_tool.py` | 3场景生成器（看涨/看跌/中性），汇合评分 |
| `risk_officer` | `src/tools/risk_officer_tool.py` | 完全否决权、9个检查点、带硬编码限制的仓位计算 |
| `portfolio` | `src/tools/portfolio_tool.py` | 投资组合评估、配置建议 |
| `decision_engine` | `src/tools/decision_engine.py` | 决策综合引擎（入场/止损/止盈1-3） |
| `pressure_engine` | `src/tools/pressure_engine.py` | 买/卖压力归一化（0.0-1.0） |
| `strategy_lifecycle` | `src/tools/strategy_lifecycle.py` | 达尔文进化：自动终止负期望策略 |

### L4：执行层

| 工具 | 文件 | 描述 |
|---|---|---|
| `execution` | `src/tools/execution_tool.py` | Paper/MT5/OANDA/Binance执行，带风险审批门 |
| `kill_switch` | `src/tools/kill_switch_tool.py` | 紧急停止、自动触发监控、手动重置 |
| `autoswitch` | `src/tools/autoswitch_engine.py` | 无缝LLM提供商故障转移（NVIDIA → Groq → OpenCode） |

### L5：学习层

| 工具 | 文件 | 描述 |
|---|---|---|
| `journal` | `src/tools/journal_tool.py` | 交易记录、PnL计算、绩效统计 |
| `auditor_research` | `src/tools/auditor_research_tool.py` | 交易审计（计划vs执行）、边缘衰退检测 |
| `audit` | `src/tools/audit_logger.py` | 从传感器到最终决策的完整追踪 |
| `backtest` | `src/tools/backtest_engine.py` | 动态点差、可变滑点、延迟模拟 |
| `math_engine` | `src/tools/math_engine.py` | 统计分析、概率计算 |

---

## 配置

所有配置通过 `config/.env` 管理（从 `config/.env.example` 复制）：

```env
# LLM提供商
NVIDIA_API_KEY=nvapi-xxxxx
GROQ_API_KEY=gsk_xxxxx
OPENCODE_API_KEY_1=xxxxx

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABC-xxxxx
TELEGRAM_CHAT_ID=123456789

# 系统
MODEL_NAME=meta/llama-3.1-nemotron-70b-instruct
LOG_DIR=./logs
DATA_DIR=./data
```

> **重要提示**：切勿将 `config/.env` 提交到版本控制。所有API密钥如果泄露必须轮换。

---

## 部署阶段

系统遵循**5阶段部署管道**。阶段推进需要用户明确批准并提供有记录的绩效指标。

| 阶段 | 名称 | 描述 | 状态 |
|---|---|---|---|
| 1 | 研究实验室 | 仅模拟交易，无真实资金 | **当前** |
| 2 | 模拟交易 | 使用真实市场数据的模拟执行 | 计划中 |
| 3 | 微型实盘 | 真实资金，最大0.01手 | 计划中 |
| 4 | 半自主 | 真实交易需用户确认 | 计划中 |
| 5 | 完全自主 | 代理独立执行（需验证优势） | 计划中 |

---

## 项目结构

```
HermesQuantOS/
├── src/
│   ├── hermes_quant.py              # 主代理控制器
│   ├── watchdog.py                  # Watchdog守护进程（10秒监控）
│   └── tools/
│       ├── __init__.py
│       ├── shared_state.py          # SharedState单例 + SQLite
│       ├── market_data_tool.py      # L1: OHLCV数据
│       ├── chart_vision_tool.py     # L1: 图表图像分析
│       ├── technical_analysis_tool.py # L2: SMC结构
│       ├── macro_sentiment_tool.py  # L2: 风险状态
│       ├── smc_agent_enhanced.py    # L2: 增强版SMC
│       ├── news_sentinel.py         # L2: 新闻影响
│       ├── market_state_engine.py   # L2: 市场状态
│       ├── strategy_tool.py         # L3: 3场景
│       ├── risk_officer_tool.py     # L3: 完全否决权
│       ├── portfolio_tool.py        # L3: 投资组合
│       ├── decision_engine.py       # L3: 决策综合
│       ├── pressure_engine.py       # L3: 压力归一化
│       ├── strategy_lifecycle.py    # L3: 达尔文进化
│       ├── execution_tool.py        # L4: 交易执行
│       ├── kill_switch_tool.py      # L4: 紧急停止
│       ├── autoswitch_engine.py     # L4: 提供商故障转移
│       ├── journal_tool.py          # L5: 交易日志
│       ├── auditor_research_tool.py # L5: 交易后审计
│       ├── audit_logger.py          # L5: 完整审计追踪
│       ├── backtest_engine.py       # L5: 回测
│       └── math_engine.py           # L5: 统计分析
├── scripts/
│   ├── keeper.py                    # Cron健康监控器
│   ├── install_termux.sh            # Android安装器
│   └── install_server.sh            # Linux安装器
├── config/
│   ├── .env.example                 # 环境模板
│   ├── hermes-quant.yaml            # 系统配置
│   └── system_prompt.py             # 交易系统提示
├── schemas/
│   └── trading_journal.sql          # 7表SQL架构
├── hermes.sh                        # 控制脚本
├── AGENTS.md                        # 运营宪法
├── CHANGELOG.md                     # 版本历史
├── ARCHITECTURE.md                  # 系统架构
├── STRUCTURE.md                     # 项目结构
├── UPGRADE_PLAN.md                  # 自主升级路线图
├── PR.md                            # PR模板与提案
├── ALL.md                           # 综合参考
├── requirements.txt                 # Python依赖
└── .gitignore                       # Git忽略规则
```

---

## 版本历史

| 版本 | 日期 | 代号 | 关键特性 |
|---|---|---|---|
| 1.0.0 | 2026-05-20 | Genesis | 11个交易工具，Hermes Agent适配 |
| 1.1.0 | 2026-05-21 | Polyglot | 多提供商LLM支持（NVIDIA + Groq + OpenCode） |
| 2.0.0 | 2026-05-22 | Immortal | 自动重启与开机启动基础设施（3层） |
| 3.0.0 | 2026-05-23 | Constitution | AGENTS.md宪政框架，硬编码风险规则 |
| 3.1.0 | 2026-05-24 | Synthesis | Quant-Nanggroe-AI 10工具集成（共21个代理） |
| 3.2.0 | 2026-05-25 | Chronicle | 文档套件与自主升级规划 |
| **4.0.0** | **2026-05-25** | **Production** | **SharedState、PnL同步、SQLite持久化、HTML Telegram、21工具路由** |

详见 [CHANGELOG.md](./CHANGELOG.md)。

---

## 路线图

| 阶段 | 特性 | 状态 |
|---|---|---|
| PR-001 | 自主交易循环 | 提议中 |
| PR-002 | 跨资产相关性监控器 | 提议中 |
| PR-003 | 达尔文策略进化 | 提议中 |
| PR-004 | Alpha Zoo集成（来自Vibe-Trading的450+因子） | 提议中 |
| PR-005 | AutoHedge集群管道 | 提议中 |
| 未来 | Docker + Kubernetes部署 | 计划中 |
| 未来 | 多租户SaaS平台 | 计划中 |
| 未来 | Web仪表板（React/Next.js） | 计划中 |
| 未来 | REST API网关 | 计划中 |
| 未来 | 多交易所实盘交易 | 计划中 |

详见 [UPGRADE_PLAN.md](./UPGRADE_PLAN.md) 了解完整的15-18个月自主升级路线图。

---

## 贡献

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&duration=3000&pause=1500&color=00FF88&center=true&vCenter=true&repeat=true&width=500&height=35&lines=欢迎贡献者！;加入自主交易革命" alt="欢迎贡献者" />

</div>

我们欢迎开发者、量化分析师、风险工程师和AI研究人员的贡献！HermesQuantOS建立在**协作产生卓越系统**的原则之上。

### 如何贡献

1. **Fork** 此仓库
2. **创建**特性分支（`git checkout -b feature/amazing-feature`）
3. **提交**您的更改（`git commit -m 'Add amazing feature'`）
4. **推送**到分支（`git push origin feature/amazing-feature`）
5. **打开**Pull Request

### 贡献领域

- **交易工具**：新的分析工具、指标或执行适配器
- **风险工程**：增强的风险检查、相关性监控器、投资组合优化
- **基础设施**：Docker配置、CI/CD管道、监控仪表板
- **AI/ML**：策略进化、因子研究、回测改进
- **文档**：翻译、教程、架构图
- **测试**：单元测试、集成测试、压力测试

### 准则

- 所有交易工具必须通过风险官——不可绕过
- 风险规则是**硬编码**且**不可协商**的——不要提交削弱它们的PR
- 遵循现有代码结构和命名约定
- 为新功能添加测试
- 使用您的更改更新文档（CHANGELOG.md、STRUCTURE.md）
- 每个PR一个功能——保持专注和可审查

---

## 联系方式

<div align="center">

### Mulky Malikul Dhaher

[![Email](https://img.shields.io/badge/邮箱-mulkymalikuldhaher@email.com-00FF88?style=for-the-badge&logo=gmail&logoColor=white&labelColor=0A0A0A)](mailto:mulkymalikuldhaher@email.com)
[![GitHub](https://img.shields.io/badge/GitHub-mulkymalikuldhrs-FF6B35?style=for-the-badge&logo=github&logoColor=white&labelColor=0A0A0A)](https://github.com/mulkymalikuldhrs)

<br/>

**项目仓库**：[github.com/mulkymalikuldhrs/HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS)

</div>

---

## 许可证

本项目采用MIT许可证——详见 [LICENSE](./LICENSE) 文件。

Nous Research原始Hermes Agent同样采用MIT许可证。

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1A1A2E,50:16213E,100:0F3460&height=80&section=footer&text=&fontSize=0&animation=fadeIn" width="100%" alt="Footer Wave" />

**HERMES QUANT OPERATING SYSTEM**

*自主。确定性。风险优先。*

<br/>

<a href="https://github.com/NousResearch/Hermes"><img src="https://img.shields.io/badge/Fork自-NousResearch/Hermes-00FF88?style=flat-square&logo=github&logoColor=white" /></a>
<img src="https://img.shields.io/badge/构建工具-Python-3776AB?style=flat-square&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/驱动-NVIDIA_AI-76B900?style=flat-square&logo=nvidia&logoColor=white" />
<img src="https://img.shields.io/badge/LLM-Groq-FF6B35?style=flat-square&logo=groq&logoColor=white" />

</div>
