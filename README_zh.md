<!-- 🦅 QUANT NANGGROE AI — 中文 README -->
<!-- Language: 中文 (Chinese) -->

<a href="https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI">
  <img align="center" src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=36&duration=3000&pause=1500&color=00D4AA&center=true&vCenter=true&multiline=true&repeat=true&width=800&height=120&lines=QUANT+NANGGROE+AI;多智能体决策智能操作系统" alt="Typing SVG" />
</a>

<div align="center">

[![版本](https://img.shields.io/badge/版本-15.2.0-gold?style=for-the-badge&logo=semver&logoColor=white)](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![许可证](https://img.shields.io/badge/许可证-MIT-green?style=for-the-badge&logo=open-source-initiative&logoColor=white)](./LICENSE)
[![状态](https://img.shields.io/badge/状态-全面运行-22C55E?style=for-the-badge&logo=checkmarx&logoColor=white)](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)

</div>

<div align="center">

**语言 / Bahasa / 语言:**
[![English](https://img.shields.io/badge/EN-English-blue?style=flat-square)](./README.md)
[![Bahasa Indonesia](https://img.shields.io/badge/ID-Bahasa_Indonesia-red?style=flat-square)](./README_id.md)
[![中文](https://img.shields.io/badge/CN-中文-yellow?style=flat-square)](./README_zh.md)

</div>

---

## 🏛️ 概述

**Quant Nanggroe AI** 是一款先进的**多智能体决策智能操作系统**，专为金融市场中的量化研究和系统化交易而设计。该平台基于**确定性决策智能**原则构建，从根本上摒弃主观AI叙述和心理偏差，代之以对原始数值数据的数学约束推理。系统将大语言模型视为**逻辑推理引擎**，而非顾问——每个引擎在严格合约下运行，禁止主观意见，强制数据锚定，并要求输出基于压力的数值结果，而非直接交易信号。

在核心层面，Quant Nanggroe AI 实现了一个**5层执行堆栈**，从原始L1/L2数据源开始，经过市场状态检测、多智能体传感器分析、压力归一化，最终到带有风险执行的决策合成。该架构灵感来自机构量化交易台，每一项决策都必须可追溯、可审计、可辩护。系统采用**达尔文策略生命周期**自动淘汰表现不佳的策略，**执行现实引擎**在回测中考虑滑点、价差和延迟，以及**风险守护宪法**作为独立硬编码安全规则层，不受AI推理影响。

前端是基于React 19和TypeScript构建的桌面OS风格界面，具有可拖拽窗口、macOS风格Dock、AI驱动命令中心（OmniBar）以及多智能体群的实时可视化。它被设计为一个完整的研究和决策支持工作站——不仅是一个仪表板，更是一个量化智能的操作环境。

> 🔗 **[HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) 统一项目** 的一部分 — 全栈量化智能生态系统。

---

## 🏗️ 系统架构

Quant Nanggroe AI 基于**5层确定性执行堆栈**构建，每一层都充当严格过滤器，要么向前传递数据，要么完全阻止。没有层可以被绕过，也没有智能体可以覆盖其上层施加的约束。这种设计确保每个交易决策都是完全可审计的确定性流水线的结果——从原始市场数据摄取到带风险许可的最终执行参数。

### 第0层：上下文神经锚定（数据基础）
整个系统的基石。该层从多个数据提供商——Binance、CoinCap、AlphaVantage、Polygon和Finnhub——收获实时L1/L2市场数据，使用**AutoSwitch**引擎实现自动故障转移和提供商健康监控。每一条进入系统的数据都带有元数据标签，包括来源、信任分数（0.0–1.0）、延迟估计、更新频率和领域类型。这些元数据向下游流动，使每个智能体和引擎能够根据数据质量权衡其置信度。**MarketService**编排所有数据访问，为价格数据、K线数据、新闻和技术指标提供统一API。

### 第1层：市场状态引擎（守门人）
**MarketStateEngine**位于所有智能体之上，作为系统的守门人。它使用ADX趋势强度、RSI极值和快速价格变化检测的组合来确定全局市场状态——`TRENDING`、`RANGE`、`MEAN_REVERT`、`RISK_OFF`、`PANIC`或`NO_TRADE`。如果市场状态为`NO_TRADE`或`PANIC`，所有下游智能体被强制进入空闲模式，在不适合的条件下保护资金。这是一个硬性约束，任何智能体或LLM推理都无法覆盖。

### 第2层：多智能体传感器（眼睛）
四个专业智能体并行运作，作为数值传感器，各自产生结构化输出类型而非主观分析：
- **QuantScanner** (`quant_scanner.ts`) — 技术动量、ADX趋势强度、波动率扩张和结构状态（BULL/BEAR/NEUTRAL）。
- **SMCAgent** (`smc_agent.ts`) — 智能货币概念：流动性清扫、位移强度和兴趣点有效性。
- **NewsSentinel** (`news_sentinel.ts`) — 宏观经济事件分类（MACRO/SCHEDULED/SHOCK/NOISE），具有对数时间衰减和方向不确定性评分。
- **FlowAgent** (`flow_agent.ts`) — 机构鲸鱼流量跟踪、COT持仓偏差（LONG/SHORT/NEUTRAL）和流量不平衡测量。

### 第3层：压力归一化引擎（编译器）
**PressureNormalizationEngine**聚合来自所有四个智能体的原始传感器输出，将其编译为两个主要向量：`BUY_PRESSURE`（0.0–1.0）和`SELL_PRESSURE`（0.0–1.0），以及波动率风险分类、流动性状况和整体置信度分数。每个传感器对压力计算贡献加权部分，具体权重源自Blueprint Final规范。该层通过将一切简化为单一归一化压力场来消除智能体信号冲突的问题。

### 第4层：决策合成引擎（裁判）
**DecisionSynthesisEngine**是最终权威。它使用**决策表**（机器可读规则）来评估当前压力状态、市场状态、波动率和置信水平是否满足入场标准。如果达到共振，**EntryRiskEngine**计算几何入场参数——入场价格、结构性止损（基于失效，而非百分比）和分层止盈（TP1：最近流动性，TP2：波动率扩展，TP3：波动率扩展x2）。风险许可由**RiskManagement**模块独立验证，该模块执行交易宪法。

---

## ⚡ 核心特性

### 🧠 确定性多智能体群
系统协调5个默认群智能体——Alpha Prime（投资组合经理）、Quant-Scanner（技术分析师）、News-Sentinel（宏观/情绪）、Risk-Guardian（风险控制）和Strategy-Weaver（算法开发者）——每个智能体具有受限的推理范围、明确的输入域和硬性约束，防止主观分析或幻觉输出。智能体通过结构化合约通信，而非自由文本。

### 🛡️ 风险守护宪法
风险管理是硬编码的，独立于AI逻辑。交易宪法执行：带有自动熔断开关的最大日回撤限制、活跃头寸之间的最大相关性（0.70阈值）、每资产最大敞口，以及基于结构性失效的止损优先于风险回报比。任何智能体都无法"推理绕过"这些规则。

### 🧬 达尔文策略生命周期
每个策略都接受统计显著性监控。如果策略的**期望值**在足够样本量（最少20笔交易）上变为负值，它会被自动标记为`KILLED`，资源转移到更高表现的变体。回撤超过15%的策略被置于`HIBERNATING`状态。这种自然选择机制确保系统持续向盈利能力进化。

### 📊 执行现实引擎
回测不是幻想。**BacktestEngine**考虑动态价差（波动率调整）、随机滑点、部分成交概率（2–15%，取决于波动率）、订单拒绝模拟和现实延迟（100–500ms）。这确保回测表现反映真实交易条件，而非理想化假设。

### 🔍 完整审计追踪
**AuditLogger**记录所有层的每个事件——市场、传感器、压力、决策、风险和执行——带有时间戳、结构化数据载荷和严重性级别。系统做出的每个决策都完全可追溯和可复现，满足机构合规要求。

### 🔄 AutoSwitch API 故障转移
**AutoSwitch**引擎提供带有指数退避重试逻辑的自动提供商故障转移、基于健康的提供商优先级排序、失败提供商的冷却机制和实时健康报告。这确保即使单个API提供商经历中断或速率限制时也能保持不间断的数据流。

### 📚 自主研究智能体
**ResearchAgent**以可配置间隔持续运行，从8+来源收获情报，包括全球新闻、市场快照、地缘政治数据、社交情绪、机构流量和AI生态系统更新。所有收获的情报持久化到知识库，用于交叉引用和历史分析。

### 🧮 机构级数学引擎
**MathEngine**提供全面的纯数学指标套件：RSI、SMA、EMA、MACD、布林带、带波段的VWAP、成交量分布、随机振荡器、CCI、ADX和ATR。每项计算100%确定性，零AI参与——消除技术分析中的幻觉风险。

---

## 🖥️ 组件描述

| 组件 | 文件 | 描述 |
|---|---|---|
| **Launchpad** | `components/Launchpad.tsx` | macOS风格的应用启动器，提供快速访问所有系统窗口和工具。以网格布局显示所有可用应用，带有动画图标和标签。 |
| **TradingTerminal** | `components/TradingTerminalWindow.tsx` | 专业交易终端，配备由Lightweight Charts v4.1驱动的实时K线图、下单界面和带有权益/保证金/盈亏显示的实时持仓追踪。 |
| **SwarmGraph** | `components/SwarmConfigModal.tsx` | 群智能配置面板，用于管理智能体能力、分配工具和监控群中每个智能体的健康和活动。 |
| **NexusWindow** | `components/NexusWindow.tsx` | Quantum Nexus可视化仪表板，显示系统一致性指标、活跃量子位、突触负载和神经处理管道的运行状态。 |
| **MarketWindow** | `components/MarketWindow.tsx` | 实时市场数据仪表板，显示价格行情、24小时变化、成交量、技术指标和追踪资产的市场状态分类。 |
| **ResearchAgentWindow** | `components/ResearchAgentWindow.tsx` | 研究情报控制台，显示自主研究日志、收获的情报摘要和所有8+情报来源的扫描状态。 |
| **KnowledgeBaseWindow** | `components/KnowledgeBaseWindow.tsx` | 知识管理界面，用于浏览、搜索和管理存储在持久知识库中的研究项目、市场分析和机构情报。 |
| **BrowserWindow** | `components/BrowserWindow.tsx` | 集成网络浏览器，可直接在Quant Nanggroe OS环境中导航金融新闻网站、研究论文和市场数据源。 |
| **PortfolioWindow** | `components/PortfolioWindow.tsx` | 投资组合管理仪表板，具备实时权益追踪、保证金状态、盈亏计算、资产配置可视化和仓位管理。 |
| **SystemArchitecture** | `components/SystemArchitecture.tsx` | 可视化系统架构图，展示5层执行堆栈、引擎间的数据流和智能体通信路径。 |
| **AgentHud** | `components/AgentHud.tsx` | 平视显示器，用于监控群智能体状态，包括当前动作、情绪、思考状态和活跃浏览器URL追踪。 |
| **ControlCenter** | `components/ControlCenter.tsx` | 系统控制面板，具有安全矩阵、风险守护仪表板、主题切换和系统配置选项。 |
| **OmniBar** | `components/OmniBar.tsx` | Spotlight风格通用命令栏，快速访问任何系统功能、市场扫描命令（`/scan`）和AI驱动搜索。 |
| **Taskbar** | `components/Taskbar.tsx` | 屏幕底部的macOS风格Dock，提供窗口管理、应用启动和系统状态指示器。 |
| **WindowFrame** | `components/WindowFrame.tsx` | 可拖拽、可调整大小的窗口容器，具有标题栏、最小化/关闭按钮、z-index管理和焦点追踪，提供桌面OS体验。 |

---

## 🚀 快速开始

### 前置条件
- **Node.js** >= 18.0.0
- **npm** >= 9.0.0（或 yarn/pnpm）
- API密钥（可选但推荐）：
  - **Google Gemini** — 用于LLM驱动的群智能
  - **Finnhub** — 用于实时市场数据
  - **AlphaVantage** — 用于股票/外汇技术数据

### 安装

```bash
# 克隆仓库
git clone https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI.git

# 进入项目目录
cd Quant-Nanggroe-AI

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 配置

1. 使用 `npm run dev` 启动应用
2. 从控制中心或任务栏打开**设置**面板
3. 在配置部分输入您的API密钥：
   - `Google API Key` — Gemini驱动的智能体群所需
   - `Finnhub API Key` — 用于实时市场数据源
   - `AlphaVantage API Key` — 用于股票技术指标
4. 系统将在启动时自动初始化存储服务（IndexedDB、BrowserFS、Memory Manager）
5. **ResearchAgent** 将立即开始自主情报收获

### 生产构建

```bash
# 创建优化的生产构建
npm run build

# 本地预览生产构建
npm run preview
```

---

## 📁 项目结构

```
Quant-Nanggroe-AI/
├── 📄 App.tsx                          # 主应用组件，带有OS风格窗口管理
├── 📄 index.tsx                         # 应用入口点
├── 📄 types.ts                          # 核心类型定义（MarketState、DecisionSynthesis、AgentContract等）
├── 📄 index.html                        # HTML入口点
├── 📄 vite.config.ts                    # Vite构建配置
├── 📄 tsconfig.json                     # TypeScript配置
├── 📄 package.json                      # 依赖和脚本
├── 📄 metadata.json                     # 系统元数据（版本、描述）
├── 📄 CHANGELOG.md                      # 版本历史和发布说明
│
├── 📂 components/                       # React UI组件
│   ├── 📄 Launchpad.tsx                 # 应用启动器
│   ├── 📄 TradingTerminalWindow.tsx     # 带图表的交易终端
│   ├── 📄 MarketWindow.tsx              # 市场数据仪表板
│   ├── 📄 PortfolioWindow.tsx           # 投资组合管理
│   ├── 📄 ResearchAgentWindow.tsx       # 研究情报控制台
│   ├── 📄 KnowledgeBaseWindow.tsx       # 知识库浏览器
│   ├── 📄 BrowserWindow.tsx             # 集成网络浏览器
│   ├── 📄 NexusWindow.tsx              # Quantum Nexus可视化
│   ├── 📄 SwarmConfigModal.tsx          # 群智能体配置
│   ├── 📄 SystemArchitecture.tsx        # 架构图
│   ├── 📄 AgentHud.tsx                  # 智能体HUD显示
│   ├── 📄 ControlCenter.tsx             # 系统控制面板
│   ├── 📄 OmniBar.tsx                   # 通用命令栏
│   ├── 📄 Taskbar.tsx                   # Dock/任务栏
│   ├── 📄 WindowFrame.tsx              # 可拖拽窗口容器
│   ├── 📄 ChatMessage.tsx              # 聊天消息组件
│   ├── 📄 InputArea.tsx                # 消息输入区域
│   ├── 📄 ArtifactWindow.tsx           # 工件显示窗口
│   ├── 📄 Avatar.tsx                   # 用户头像组件
│   ├── 📄 RealTimeChart.tsx            # 实时图表组件
│   ├── 📄 SystemUpdater.tsx            # 系统更新检查器
│   └── 📄 Icons.tsx                    # SVG图标库
│
├── 📂 services/                         # 核心业务逻辑和引擎
│   ├── 📄 strategy_engine.ts           # 策略评估（SMC、S/R、零售TA）
│   ├── 📄 quantum_engine.ts            # 压力归一化和决策合成
│   ├── 📄 decision_synthesis_engine.ts  # 决策表和合成逻辑
│   ├── 📄 pressure_normalization_engine.ts # 传感器到压力编译
│   ├── 📄 market_state_engine.ts       # 市场状态检测（第1层）
│   ├── 📄 entry_risk_engine.ts         # 入场几何和风险计算
│   ├── 📄 smc_agent.ts                # 智能货币概念传感器
│   ├── 📄 news_sentinel.ts             # 新闻和宏观事件分类
│   ├── 📄 flow_agent.ts               # 机构流量追踪
│   ├── 📄 quant_scanner.ts            # 量化动量扫描器
│   ├── 📄 math_engine.ts              # 纯数学指标
│   ├── 📄 ml_engine.ts                # 机器学习工具
│   ├── 📄 backtest_engine.ts          # 带执行现实的回测
│   ├── 📄 strategy_lifecycle.ts        # 达尔文策略管理
│   ├── 📄 audit_logger.ts             # 完整审计追踪系统
│   ├── 📄 autoswitch.ts               # API故障转移引擎
│   ├── 📄 research_agent.ts           # 自主研究收获器
│   ├── 📄 knowledge_base.ts           # 持久知识存储
│   ├── 📄 browser_core.ts             # 浏览器导航控制器
│   ├── 📄 llm_router.ts              # 多LLM路由引擎
│   ├── 📄 gemini.ts                   # Google Gemini AI集成
│   ├── 📄 market.ts                   # 市场数据服务（统一API）
│   ├── 📄 risk_management.ts          # 风险守护执行
│   ├── 📄 correlation_monitor.ts      # 资产相关性追踪
│   ├── 📄 memory_manager.ts           # 会话内存管理
│   ├── 📄 storage_manager.ts          # 混合存储编排
│   ├── 📄 storage_adapter.ts          # 存储适配器模式
│   ├── 📄 file_system.ts             # 基于浏览器的文件系统
│   ├── 📄 drive.ts                   # 虚拟驱动器管理
│   ├── 📄 adaptive_layout.ts          # 响应式布局引擎
│   ├── 📄 evolution_monitor.ts        # 策略进化追踪
│   ├── 📄 backup_service.ts           # 系统备份和恢复
│   └── 📄 desktop_intelligence.ts     # 桌面AI集成
│
└── 📂 docs/                            # 文档
    ├── 📄 ARCHITECTURE.md              # 系统架构参考
    ├── 📄 BLUEPRINT.md                 # 设计蓝图
    ├── 📄 BUILD_PLAN.md               # 构建路线图
    ├── 📄 EVOLUTION_MANIFEST.md       # 策略进化哲学
    ├── 📄 SERVICES_GUIDE.md           # 服务文档
    ├── 📄 STORAGE.md                  # 存储架构
    ├── 📄 SYSTEM_AUDIT_LOG.md         # 系统审计参考
    └── 📄 USER_GUIDE.md              # 用户指南
```

---

## 🤝 参与贡献

我们欢迎来自世界各地的贡献者！Quant Nanggroe AI 是一个雄心勃勃的项目，位于量化金融、人工智能和系统工程三大领域的交汇点。无论您是经验丰富的量化开发者、React/TypeScript专家、机器学习研究员，还是对构建智能交易系统充满热情的人——这里都有您的一席之地。

### 如何贡献

1. **Fork** 仓库：[https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)
2. **创建** 功能分支：`git checkout -b feature/your-feature-name`
3. **提交** 您的更改，附带清晰、描述性的提交信息
4. **推送** 到您的fork：`git push origin feature/your-feature-name`
5. **发起** Pull Request，详细描述您的更改

### 需要帮助的领域

- 🧪 **测试** — 所有引擎的单元测试、集成测试和端到端测试
- 📊 **指标** — MathEngine的额外技术指标（一目均衡表、斐波那契、艾略特波浪）
- 🔌 **数据提供商** — 新API集成（Yahoo Finance、CoinGecko、TradingView）
- 🎨 **UI/UX** — 组件改进、可访问性、移动端响应性
- 📖 **文档** — API文档、教程和示例
- 🌐 **国际化** — 翻译和本地化支持
- 🏗️ **云端部署** — Docker、Kubernetes和云原生部署配置

### 开发准则

- 所有TypeScript代码必须通过严格类型检查（`strict: true`）
- 遵循现有项目结构和命名约定
- 每个新服务必须包含通过`AuditLogger`的审计日志
- 所有金融计算必须是确定性和可测试的
- UI组件必须支持浅色和深色主题

### 联系方式

如有问题、建议或合作咨询，请联系：

[![Email](https://img.shields.io/badge/Email-mulkymalikuldhaher@email.com-EA4335?style=flat-square&logo=gmail&logoColor=white)](mailto:mulkymalikuldhaher@email.com)
[![GitHub](https://img.shields.io/badge/GitHub-mulkymalikuldhrs-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/mulkymalikuldhrs)

---

## 🔗 相关项目

| 项目 | 描述 | 链接 |
|---|---|---|
| **HermesQuantOS** | 统一量化智能生态系统 — 整合Quant Nanggroe AI与后端服务的父项目 | [https://github.com/mulkymalikuldhrs/HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) |

---

## 📜 许可证

本项目基于MIT许可证授权。详见 [LICENSE](./LICENSE) 文件。

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0D9488,50:065F46,100:020205&height=120&section=footer" width="100%" />
</p>

<p align="center">
  <strong>&copy; 2026 Quant Nanggroe AI</strong><br/>
  由 <a href="https://github.com/mulkymalikuldhrs">Mulky Malikul Dhaher</a> 用 💎 构建<br/>
  <em>期待来自世界各地的贡献者 🌎</em>
</p>
