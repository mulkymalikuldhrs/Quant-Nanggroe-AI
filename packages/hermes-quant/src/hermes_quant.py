#!/usr/bin/env python3
"""
HERMES QUANT OPERATING SYSTEM - Main Agent
============================================
Autonomous Multi-Agent Trading & Research Infrastructure
Owner: Mulky Malikul Dhaher

Architecture: 21 Agents across 5 Layers
  L1 Data:    Market Data Agent, Chart Vision Agent
  L2 Analysis: Technical Analyst, Macro/Fundamental, Sentiment
  L3 Decision: Strategy Agent, Risk Officer (FULL VETO), Portfolio Manager
  L4 Execution: Execution Agent, Kill Switch
  L5 Learning: Journal Agent, Post-Trade Auditor, Research/Improvement

Risk Rules (HARDCODED, NO OVERRIDE):
  - 0.5% max risk per trade
  - 1% daily max loss
  - 3% weekly max loss

Deployment Stage: Research Lab (Stage 1)
Based on: Hermes Agent (Nous Research) + AGENTS.md Constitutional Framework
"""

import os
import re
import sys
import json
import signal
import logging
import asyncio
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Import Trading Tools
sys.path.insert(0, str(Path(__file__).parent))
try:
    from tools.shared_state import get_shared_state
    from tools.market_data_tool import MarketDataTool
    from tools.technical_analysis_tool import TechnicalAnalysisTool
    from tools.risk_officer_tool import RiskOfficerTool
    from tools.execution_tool import ExecutionTool
    from tools.kill_switch_tool import KillSwitchTool
    from tools.journal_tool import JournalTool
    from tools.strategy_tool import StrategyTool
    from tools.macro_sentiment_tool import MacroSentimentTool
    from tools.portfolio_tool import PortfolioTool
    from tools.auditor_research_tool import AuditorResearchTool
    from tools.chart_vision_tool import ChartVisionTool
    from tools.pressure_engine import PressureNormalizationEngine
    from tools.decision_engine import DecisionSynthesisEngine
    from tools.market_state_engine import MarketStateEngine
    from tools.news_sentinel import NewsSentinelTool
    from tools.strategy_lifecycle import StrategyLifecycleManager
    from tools.math_engine import MathEngine
    from tools.backtest_engine import BacktestEngine
    from tools.autoswitch_engine import AutoSwitchEngine
    from tools.smc_agent_enhanced import SMCAgentEnhanced
    from tools.audit_logger import AuditLogger
    TOOLS_AVAILABLE = True
except ImportError as e:
    TOOLS_AVAILABLE = False
    print(f"[WARN] Trading tools import failed: {e}")

# Load environment
ENV_PATH = Path(__file__).parent.parent / "config" / ".env"
load_dotenv(ENV_PATH)

# ===========================================
# CONFIGURATION - MULTI-PROVIDER
# ===========================================

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_API_BASE = os.getenv("OPENAI_API_BASE", "https://integrate.api.nvidia.com/v1")

GROQ_API_KEYS = [
    os.getenv("GROQ_API_KEY", ""),
    os.getenv("GROQ_API_KEY_2", ""),
    os.getenv("GROQ_API_KEY_3", ""),
    os.getenv("GROQ_API_KEY_4", ""),
    os.getenv("GROQ_API_KEY_5", ""),
    os.getenv("GROQ_API_KEY_6", "")
]
GROQ_API_KEYS = [k for k in GROQ_API_KEYS if k]
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")

OPENCODE_API_KEYS = [
    os.getenv("OPENCODE_API_KEY_1", ""),
    os.getenv("OPENCODE_API_KEY_2", "")
]
OPENCODE_API_KEYS = [k for k in OPENCODE_API_KEYS if k]
OPENCODE_API_BASE = os.getenv("OPENCODE_API_BASE", "https://api.opencode.ai/v1")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

MODEL_NAME = os.getenv("MODEL_NAME", "meta/llama-3.1-nemotron-70b-instruct")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

LOG_DIR = Path(os.getenv("LOG_DIR", str(Path(__file__).parent.parent / "logs")))
MEMORY_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent / "data")))
SESSION_LOG = MEMORY_DIR / "sessions.json"
MAX_RESTART_ATTEMPTS = int(os.getenv("MAX_RESTART_ATTEMPTS", "0"))  # 0 = unlimited
RESTART_DELAY = int(os.getenv("RESTART_DELAY", "5"))

# ===========================================
# RISK RULES - Imported from risk_officer_tool (single source of truth)
# ===========================================

try:
    from tools.risk_officer_tool import MAX_RISK_PER_TRADE as RISK_MAX_PER_TRADE
    from tools.risk_officer_tool import MAX_DAILY_LOSS as RISK_DAILY_MAX
    from tools.risk_officer_tool import MAX_WEEKLY_LOSS as RISK_WEEKLY_MAX
except ImportError:
    RISK_MAX_PER_TRADE = 0.005     # 0.5%  (fallback if import fails)
    RISK_DAILY_MAX = 0.01          # 1%    (fallback if import fails)
    RISK_WEEKLY_MAX = 0.03         # 3%    (fallback if import fails)

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"hermes_quant_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("HermesQuantOS")

# ===========================================
# AGENTS.MD SYSTEM PROMPT
# ===========================================

AGENTS_SYSTEM_PROMPT = f"""Kamu adalah HERMES QUANT OPERATING SYSTEM - sistem trading otonom berdasarkan prinsip AGENTS.md.

## IDENTITAS & KONTEKS (WAJIB DIINGAT)
- **Nama:** Hermes Quant OS
- **Owner:** Mulky Malikul Dhaher
- **Mission:** Autonomous multi-agent trading & research untuk consistent capital growth
- **Target Markets:** Forex (XAUUSD, major pairs), Crypto (SHIB, TRX), Polymarket
- **Deployment Stage:** Research Lab (Stage 1 - paper trading only)

## WALLET TARGETS (SEMUA DANA DIKUMPULKAN DI SINI)
- **Tron (PRIORITAS):** {os.getenv("WALLET_TRON", "NOT_CONFIGURED")}
- **Shiba Inu:** {os.getenv("WALLET_SHIBA", "NOT_CONFIGURED")}

## RISK RULES (HARDCODED, TIDAK BOLEH DILANGGAR)
- Max risk per trade: 0.5%
- Daily max loss: 1%
- Weekly max loss: 3%
- Risk Officer memiliki FULL VETO - tidak bisa di-override oleh agent manapun
- Kill switch otomatis aktif jika batas terlampaui

## 21 AGENT LAYER
L1 Data: Market Data Agent, Chart Vision Agent
L2 Analysis: Technical Analyst, Macro/Sentiment, SMC Enhanced, News Sentinel, Market State Engine
L3 Decision: Strategy Agent, Risk Officer (FULL VETO), Portfolio Manager, Decision Engine, Pressure Engine, Strategy Lifecycle
L4 Execution: Execution Agent, Kill Switch, Auto-Switch Engine
L5 Learning: Journal Agent, Post-Trade Auditor, Research/Improvement, Audit Logger, Backtest Engine, Math Engine

## TRADING FRAMEWORK
- Top Down Framework: Higher TF → Lower TF
- SMC Continuation Bias: BOS > CHoCH for entries
- 3 Scenario Analysis: Bullish / Bearish / Neutral (wajib sebelum entry)
- Confluence Scoring: Min 3/5 confluences required

## Prinsip Inti (NON-NEGOTIABLE):
1. Autonomous by default - bertindak tanpa menunggu perintah mikro
2. User is final authority - risiko besar / real money → WAJIB konfirmasi
3. Reality > Politeness - jawaban lugas, kritis, tanpa basa-basi
4. Consistency over novelty - tidak lompat ide tanpa justifikasi
5. Everything has consequence - setiap aksi dianalisis dampaknya
6. Single Source of Truth - AGENTS.md > prompt > chat > asumsi

## Mode Operasi (selalu aktif simultan):
- THINK: Analisis konteks, deteksi inkonsistensi, mapping dependensi
- PLAN: Langkah berurutan, prioritas, estimasi risiko
- ACT: Eksekusi, trading operations, dokumentasi
- AUDIT: Logging, deteksi penyimpangan, self-review

## Decision Framework:
Sebelum setiap keputusan trading:
1. Apakah ini mendekatkan ke tujuan akhir (consistent capital growth)?
2. Apakah risk/reward ratio memenuhi standar (min 1:2)?
3. Apakah Risk Officer sudah approve?
4. Apa worst-case scenario dan apakah bisa ditanggung?

Jika tidak lolos → JANGAN EKSEKUSI.

## Communication Style:
- To the point, jujur, kritis, analitis
- Dilarang: menghibur tanpa solusi, normatif, emosi sesaat
- Jika ide buruk → WAJIB tolak
- Jika user salah → WAJIB bilang

## TOOL SYSTEM - KEMAMPUAN TRADING
Hermes Quant OS memiliki 21 trading tools:

L1 Data:
1. market_data: OHLCV, economic calendar, market overview
2. chart_vision: Chart image analysis via vision LLM

L2 Analysis:
3. technical_analysis: SMC structure (BOS/CHoCH/OB/FVG/sweeps), indicators
4. macro_sentiment: Risk-on/off regime, sentiment analysis
5. smc_enhanced: Order Blocks, FVG, Liquidity Sweeps
6. news_sentinel: Macro impact scoring with log time decay
7. market_state: Market Regime Engine (TRENDING/RANGE/RISK_OFF/NO_TRADE)

L3 Decision:
8. strategy: 3-scenario generator, confluence scoring
9. risk_officer: FULL VETO, 9 checkpoints, lot sizing (HARDCODED limits)
10. portfolio: Portfolio assessment, allocation suggestions
11. decision_engine: Decision Synthesis (Entry/SL/TP1-3)
12. pressure_engine: BUY/SELL pressure normalization (0.0-1.0)
13. strategy_lifecycle: Darwinian evolution (auto-KILL negative expectancy)

L4 Execution:
14. execution: Paper/MT5/OANDA/Binance execution
15. kill_switch: Emergency halt, auto-trigger monitoring
16. autoswitch: Seamless LLM provider failover

L5 Learning:
17. journal: Trade logging, PnL calculation, performance stats
18. auditor_research: Trade audit, edge decay detection, strategy refinement
19. audit: Full trail from sensor to decision
20. backtest: Dynamic Spread, Slippage, Latency simulation
21. math_engine: Statistical analysis, probability calculations

Format: [TOOL:tool_name]argument1|argument2[/TOOL]
Contoh: [TOOL:market_data]XAUUSD|1h|50[/TOOL]
Contoh: [TOOL:risk_check]XAUUSD|BUY|0.01|2150|2140[/TOOL]

---
Hermes Quant OS bukan sekadar asisten. Ini adalah sistem trading otonom yang menjaga arah, kualitas, dan efisiensi modal. Semua keputusan trading harus melewati Risk Officer. Tidak ada pengecualian."""


class HermesQuantOS:
    """HERMES QUANT OPERATING SYSTEM - Main Agent Controller"""

    def __init__(self):
        self.running = True
        self.restart_count = 0
        self.last_error = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.conversation_history = []
        self.decisions_log = []
        self.current_provider = "groq"
        self.groq_key_index = 0
        self.opencode_key_index = 0
        self.last_update_id = 0
        self.processed_messages = set()
        self.start_time = datetime.now()

        # Shared State (SQLite persistence, single PnL source)
        self.shared_state = None

        # Initialize Trading Tools
        self.tools = {}
        if TOOLS_AVAILABLE:
            try:
                # Initialize SharedState first — single source of truth
                db_path = str(MEMORY_DIR / "hermes_quant.db")
                self.shared_state = get_shared_state(db_path)

                # Use SHARED instances for stateful tools
                shared_risk_officer = self.shared_state.risk_officer
                shared_kill_switch = self.shared_state.kill_switch
                shared_journal = self.shared_state.journal

                self.tools = {
                    # L1: Data Layer
                    "market_data": MarketDataTool(),
                    "chart_vision": ChartVisionTool(),
                    # L2: Analysis Layer
                    "technical_analysis": TechnicalAnalysisTool(),
                    "macro_sentiment": MacroSentimentTool(),
                    "smc_enhanced": SMCAgentEnhanced(),
                    "news_sentinel": NewsSentinelTool(),
                    "market_state": MarketStateEngine(),
                    # L3: Decision Layer (SHARED risk_officer)
                    "strategy": StrategyTool(),
                    "risk_officer": shared_risk_officer,
                    "portfolio": PortfolioTool(),
                    "decision_engine": DecisionSynthesisEngine(),
                    "pressure_engine": PressureNormalizationEngine(),
                    "strategy_lifecycle": StrategyLifecycleManager(),
                    # L4: Execution Layer (SHARED kill_switch, shared risk_officer via shared_state)
                    "execution": ExecutionTool(shared_state=self.shared_state),
                    "kill_switch": shared_kill_switch,
                    "autoswitch": AutoSwitchEngine(),
                    # L5: Learning Layer (SHARED journal)
                    "journal": shared_journal,
                    "auditor_research": AuditorResearchTool(),
                    "audit": AuditLogger(log_dir=str(LOG_DIR)),
                    "backtest": BacktestEngine(),
                    "math_engine": MathEngine(),
                }
                logger.info(f"Initialized {len(self.tools)} trading tools across 5 layers")
            except Exception as e:
                logger.error(f"Tool initialization failed: {e}")

        # Load previous memory
        self.load_memory()

    def get_groq_key(self) -> Optional[str]:
        if not GROQ_API_KEYS:
            return None
        key = GROQ_API_KEYS[self.groq_key_index]
        self.groq_key_index = (self.groq_key_index + 1) % len(GROQ_API_KEYS)
        return key

    def get_opencode_key(self) -> Optional[str]:
        if not OPENCODE_API_KEYS:
            return None
        key = OPENCODE_API_KEYS[self.opencode_key_index]
        self.opencode_key_index = (self.opencode_key_index + 1) % len(OPENCODE_API_KEYS)
        return key

    def load_memory(self):
        try:
            if SESSION_LOG.exists():
                with open(SESSION_LOG, 'r') as f:
                    data = json.load(f)
                    self.conversation_history = data.get('history', [])
                    self.decisions_log = data.get('decisions', [])
                    # PnL is now in shared RiskOfficer - loaded via SharedState._restore_state()
                    # self.daily_pnl / self.weekly_pnl are DEPRECATED
                    logger.info(f"Loaded {len(self.conversation_history)} previous conversations")
        except Exception as e:
            logger.warning(f"Could not load memory: {e}")

    def save_memory(self):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Get PnL from shared RiskOfficer (single source of truth)
            risk_officer = self.tools.get('risk_officer') if self.tools else None
            daily_pnl = risk_officer.daily_pnl if risk_officer else 0.0
            weekly_pnl = risk_officer.weekly_pnl if risk_officer else 0.0

            json_data = {
                'history': self.conversation_history[-100:],
                'decisions': self.decisions_log[-50:],
                'daily_pnl': daily_pnl,
                'weekly_pnl': weekly_pnl,
                'last_update': datetime.now().isoformat(),
                'session_id': self.session_id
            }
            with open(SESSION_LOG, 'w') as f:
                json.dump(json_data, f, indent=2)

            # Markdown memory export
            md_path = MEMORY_DIR / f"memory_{timestamp}.md"
            with open(md_path, 'w') as f:
                f.write(f"# Hermes Quant OS Memory - {timestamp}\n\n")
                f.write(f"## Session: {self.session_id}\n")
                f.write(f"## Last Update: {datetime.now().isoformat()}\n")
                f.write(f"## Daily PnL: {daily_pnl:.2%}\n")
                f.write(f"## Weekly PnL: {weekly_pnl:.2%}\n\n")

                f.write("## Recent Conversations\n\n")
                for item in self.conversation_history[-20:]:
                    f.write(f"**User**: {item.get('user', '')[:200]}\n\n")
                    f.write(f"**Hermes**: {item.get('hermes', '')[:200]}\n\n")
                    f.write(f"Time: {item.get('timestamp', '')}\n\n---\n\n")

                f.write("\n## Decisions Log\n\n")
                for item in self.decisions_log[-20:]:
                    f.write(f"- [{item.get('timestamp', '')}] {item.get('type', 'decision')}: "
                            f"{item.get('reasoning', item.get('error', ''))}\n")

            # Keep last 10 memory files
            md_files = sorted(MEMORY_DIR.glob("memory_*.md"))
            for old_file in md_files[:-10]:
                old_file.unlink()

            logger.info(f"Memory saved: {len(self.conversation_history)} conversations")
        except Exception as e:
            logger.error(f"Could not save memory: {e}")

    def log_decision(self, prompt, response, reasoning, provider=None):
        self.decisions_log.append({
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt[:200],
            'response_length': len(response),
            'reasoning': reasoning,
            'provider': provider or self.current_provider
        })
        self.save_memory()

    def decision_framework(self, prompt):
        """Apply AGENTS.md decision framework with trading-specific checks"""
        prompt_lower = prompt.lower()

        # High-risk trading operations requiring confirmation
        high_risk_keywords = ['execute trade', 'open position', 'place order', 'buy now',
                             'sell now', 'market order', 'real money', 'live trade',
                             'hapus', 'delete', 'reset', 'format', 'ubah arsitektur',
                             'rm -rf', 'drop table', 'override risk', 'skip risk']

        for keyword in high_risk_keywords:
            if keyword in prompt_lower:
                return {
                    'action': 'NEED_CONFIRMATION',
                    'reasoning': f'Detected high-risk operation: {keyword}',
                    'message': f'**KONFIRMASI DIPERLUKAN**\n\n'
                               f'Terdeteksi operasi berisiko tinggi: `{keyword}`\n\n'
                               f'Apakah Anda yakin ingin melanjutkan?\n\n'
                               f'Ketik YA untuk konfirmasi, atau berikan instruksi lain.'
                }

        # Check risk limits using SHARED RiskOfficer (single source of truth)
        risk_officer = self.tools.get('risk_officer') if self.tools else None
        daily_pnl = risk_officer.daily_pnl if risk_officer else 0.0
        weekly_pnl = risk_officer.weekly_pnl if risk_officer else 0.0

        # Only check LOSSES (negative PnL), not gains
        daily_loss = abs(daily_pnl) if daily_pnl < 0 else 0.0
        weekly_loss = abs(weekly_pnl) if weekly_pnl < 0 else 0.0

        if daily_loss >= RISK_DAILY_MAX:
            return {
                'action': 'BLOCKED',
                'reasoning': f'Daily loss limit reached: -{daily_loss:.2%} >= {RISK_DAILY_MAX:.2%}',
                'message': f'<b>KILL SWITCH AKTIF - DAILY LIMIT</b>\n\n'
                           f'Daily PnL: {daily_pnl:.2%}\n'
                           f'Daily Loss: -{daily_loss:.2%}\n'
                           f'Max Daily Loss: {RISK_DAILY_MAX:.2%}\n\n'
                           f'Trading dihentikan untuk hari ini. Risk rules tidak bisa di-override.'
            }

        if weekly_loss >= RISK_WEEKLY_MAX:
            return {
                'action': 'BLOCKED',
                'reasoning': f'Weekly loss limit reached: -{weekly_loss:.2%} >= {RISK_WEEKLY_MAX:.2%}',
                'message': f'<b>KILL SWITCH AKTIF - WEEKLY LIMIT</b>\n\n'
                           f'Weekly PnL: {weekly_pnl:.2%}\n'
                           f'Weekly Loss: -{weekly_loss:.2%}\n'
                           f'Max Weekly Loss: {RISK_WEEKLY_MAX:.2%}\n\n'
                           f'Trading dihentikan untuk minggu ini. Risk rules tidak bisa di-override.'
            }

        return {'action': 'PROCEED', 'reasoning': 'Low risk, proceeding with response'}

    async def start(self):
        """Main entry point for Hermes Quant OS"""
        logger.info("=" * 60)
        logger.info("HERMES QUANT OPERATING SYSTEM STARTING")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"NVIDIA Model: {MODEL_NAME}")
        logger.info(f"Groq Model: {GROQ_MODEL}")
        logger.info(f"Groq Keys: {len(GROQ_API_KEYS)}")
        logger.info(f"OpenCode Keys: {len(OPENCODE_API_KEYS)}")
        logger.info(f"Trading Tools: {len(self.tools)}")
        logger.info(f"Risk Rules: {RISK_MAX_PER_TRADE:.1%}/{RISK_DAILY_MAX:.1%}/{RISK_WEEKLY_MAX:.1%}")
        logger.info(f"Deployment: Research Lab (Stage 1)")
        logger.info("AGENTS.md Principles: ACTIVE")
        logger.info("=" * 60)

        self.decisions_log.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'SESSION_START',
            'session_id': self.session_id,
            'providers': {
                'nvidia': bool(NVIDIA_API_KEY),
                'groq': len(GROQ_API_KEYS),
                'opencode': len(OPENCODE_API_KEYS)
            },
            'tools_loaded': list(self.tools.keys())
        })
        self.save_memory()

        await self.send_telegram_message(
            f"<b>HERMES QUANT OS STARTED</b>\n\n"
            f"Session: {self.session_id}\n"
            f"Tools: {len(self.tools)} loaded\n"
            f"Risk: {RISK_MAX_PER_TRADE:.1%}/{RISK_DAILY_MAX:.1%}/{RISK_WEEKLY_MAX:.1%}\n"
            f"Stage: Research Lab (Paper Only)\n"
            f"Providers: NVIDIA + Groq ({len(GROQ_API_KEYS)}) + OpenCode ({len(OPENCODE_API_KEYS)})\n\n"
            f"AGENTS.md: Active | Auto-restart: Enabled"
        )

        while self.running:
            try:
                await self.run_agent_loop()
            except Exception as e:
                self.last_error = str(e)
                logger.error(f"Error in agent loop: {e}\n{traceback.format_exc()}")
                await self.handle_crash(e)

    async def run_agent_loop(self):
        """Main agent loop - continuous Telegram polling"""
        while self.running:
            try:
                updates = await self.get_telegram_updates()
                for update in updates:
                    await self.process_telegram_update(update)
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Error in run loop: {e}")
                raise

    async def get_telegram_updates(self):
        import aiohttp
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"timeout": 5, "limit": 100, "offset": self.last_update_id + 1}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("result", [])
        except Exception as e:
            logger.debug(f"Telegram poll: {e}")
        return []

    async def process_telegram_update(self, update):
        if "message" not in update:
            return

        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"].get("text", "")
        message_id = update["message"].get("message_id", 0)

        update_id = update.get("update_id", 0)
        if update_id > self.last_update_id:
            self.last_update_id = update_id

        if message_id in self.processed_messages:
            return
        self.processed_messages.add(message_id)
        if len(self.processed_messages) > 100:
            self.processed_messages = set(list(self.processed_messages)[-100:])

        if chat_id != TELEGRAM_CHAT_ID or not text:
            return

        logger.info(f"Telegram: {text[:100]}")

        # Handle commands
        if text.startswith("/"):
            await self.handle_command(text)
            return

        # Apply decision framework
        decision = self.decision_framework(text)

        if decision['action'] == 'BLOCKED':
            await self.send_telegram_message(decision['message'])
            return

        if decision['action'] == 'NEED_CONFIRMATION':
            await self.send_telegram_message(decision['message'])
            return

        # Process tool calls
        response = await self.process_with_tools(text)

        if not response:
            response = await self.generate_response(text)

        self.log_decision(text, response, decision['reasoning'])
        await self.send_telegram_message(response)

        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'user': text,
            'hermes': response,
            'session': self.session_id
        })

        if len(self.conversation_history) % 5 == 0:
            self.save_memory()

    async def process_with_tools(self, text):
        """Process text for embedded tool calls like [TOOL:name]args[/TOOL]"""
        import re
        tool_pattern = r'\[TOOL:(\w+)\](.*?)\[/TOOL\]'
        matches = re.findall(tool_pattern, text)

        if not matches:
            # Check if text implies a tool use
            text_lower = text.lower()
            if any(kw in text_lower for kw in ['market data', 'price', 'ohlcv', 'candle']):
                if 'market_data' in self.tools:
                    symbol = 'XAUUSD'
                    for s in ['xauusd', 'eurusd', 'gbpusd', 'btcusdt', 'shib', 'trx']:
                        if s in text_lower:
                            symbol = s.upper()
                            break
                    result = self.tools['market_data'].get_ohlcv(symbol, '1h', 50)
                    return f"Market Data - {symbol}:\n{result}"

            if any(kw in text_lower for kw in ['analisis teknikal', 'technical', 'support', 'resistance', 'smc']):
                if 'technical_analysis' in self.tools:
                    symbol = 'XAUUSD'
                    for s in ['xauusd', 'eurusd', 'gbpusd', 'btcusdt']:
                        if s in text_lower:
                            symbol = s.upper()
                            break
                    result = self.tools['technical_analysis'].analyze(symbol, '1h')
                    return f"Technical Analysis - {symbol}:\n{result}"

            if any(kw in text_lower for kw in ['risk check', 'risk assessment', 'lot size']):
                if 'risk_officer' in self.tools:
                    result = self.tools['risk_officer'].status()
                    return f"Risk Officer Status:\n{result}"

            if any(kw in text_lower for kw in ['status', 'system', 'health']):
                return self.get_system_status()

            return None

        results = []
        for tool_name, args_str in matches:
            if tool_name in self.tools:
                try:
                    args = args_str.split('|') if '|' in args_str else [args_str]
                    tool = self.tools[tool_name]

                    # Route to appropriate tool method
                    if tool_name == 'market_data':
                        result = tool.get_ohlcv(*args[:3]) if len(args) >= 1 else tool.get_market_overview()
                    elif tool_name == 'technical_analysis':
                        result = tool.analyze(*args[:2]) if len(args) >= 1 else tool.analyze('XAUUSD', '1h')
                    elif tool_name == 'risk_officer':
                        result = tool.check_trade(*args[:5]) if len(args) >= 4 else tool.status()
                    elif tool_name == 'execution':
                        result = tool.paper_trade(*args[:5]) if len(args) >= 4 else tool.status()
                    elif tool_name == 'kill_switch':
                        result = tool.activate() if 'activate' in args_str.lower() else tool.status()
                    elif tool_name == 'journal':
                        result = tool.log_trade(*args[:6]) if len(args) >= 4 else tool.get_stats()
                    elif tool_name == 'strategy':
                        result = tool.generate_scenarios(*args[:2]) if len(args) >= 1 else tool.generate_scenarios('XAUUSD')
                    elif tool_name == 'macro_sentiment':
                        result = tool.get_regime() if 'regime' in args_str.lower() else tool.get_sentiment()
                    elif tool_name == 'portfolio':
                        result = tool.assess() if 'assess' in args_str.lower() else tool.status()
                    elif tool_name == 'auditor_research':
                        result = tool.audit_recent() if 'audit' in args_str.lower() else tool.suggest_improvements()
                    elif tool_name == 'chart_vision':
                        result = tool.analyze_chart(args[0]) if len(args) >= 1 else "No image path provided"
                    # ── L2: Analysis Layer ──
                    elif tool_name == 'smc_enhanced':
                        smc_symbol = args[0] if len(args) >= 1 else 'XAUUSD'
                        smc_data_raw = self.tools['market_data'].get_ohlcv(smc_symbol, '1h', 50)
                        try:
                            smc_parsed = json.loads(smc_data_raw)
                            smc_data = smc_parsed.get('data', [])
                        except Exception:
                            smc_data = []
                        if smc_data:
                            result = tool.analyze(smc_data, symbol=smc_symbol)
                        else:
                            result = json.dumps({"error": f"No market data available for {smc_symbol}"})
                    elif tool_name == 'news_sentinel':
                        result = tool.score_impact(args[0], args[1] if len(args) > 1 else 'medium') if len(args) >= 1 else tool.get_recent_events()
                    elif tool_name == 'market_state':
                        ms_symbol = args[0] if len(args) >= 1 else 'XAUUSD'
                        result = tool.detect_regime(symbol=ms_symbol)
                    # ── L3: Decision Layer ──
                    elif tool_name == 'decision_engine':
                        result = tool.synthesize(args[0]) if len(args) >= 1 else tool.status()
                    elif tool_name == 'pressure_engine':
                        result = tool.normalize(args[0]) if len(args) >= 1 else tool.status()
                    elif tool_name == 'strategy_lifecycle':
                        if 'kill' in args_str.lower() or 'list' in args_str.lower():
                            result = tool.get_strategy_report()
                        else:
                            result = tool.get_strategy_report()
                    # ── L4: Execution Layer ──
                    elif tool_name == 'autoswitch':
                        result = tool.get_status() if hasattr(tool, 'get_status') else "AutoSwitch active"
                    # ── L5: Learning Layer ──
                    elif tool_name == 'audit':
                        result = tool.get_entries() if hasattr(tool, 'get_entries') else tool.get_summary() if hasattr(tool, 'get_summary') else str(len(tool.entries)) + " audit entries" if hasattr(tool, 'entries') else "Audit logger active"
                    elif tool_name == 'backtest':
                        result = tool.run(args[0]) if len(args) >= 1 and hasattr(tool, 'run') else tool.status() if hasattr(tool, 'status') else "Backtest engine ready"
                    elif tool_name == 'math_engine':
                        result = tool.status() if hasattr(tool, 'status') else "Math engine ready"
                    else:
                        result = f"Unknown tool method for {tool_name}"

                    results.append(f"[{tool_name}] {result}")
                except Exception as e:
                    results.append(f"[{tool_name}] ERROR: {e}")
            else:
                results.append(f"[{tool_name}] Tool not available")

        return "\n\n".join(results)

    async def handle_command(self, text):
        """Handle Telegram bot commands"""
        cmd = text.split()[0].lower()

        if cmd == "/start":
            await self.send_telegram_message(
                "<b>HERMES QUANT OPERATING SYSTEM</b>\n\n"
                "Sistem trading otonom berbasis AGENTS.md\n"
                f"Tools: {len(self.tools)} | Risk: {RISK_MAX_PER_TRADE:.1%}/{RISK_DAILY_MAX:.1%}/{RISK_WEEKLY_MAX:.1%}\n"
                "Stage: Research Lab (Paper Only)\n\n"
                "<b>Commands:</b>\n"
                "/start - Pesan ini\n"
                "/status - Status sistem\n"
                "/market [symbol] - Data market\n"
                "/analyze [symbol] - Analisis teknikal\n"
                "/risk - Status Risk Officer\n"
                "/strategy [symbol] - 3 scenario analysis\n"
                "/journal - Trade journal stats\n"
                "/kill - Kill switch status\n"
                "/help - Bantuan lengkap"
            )

        elif cmd == "/status":
            await self.send_telegram_message(self.get_system_status())

        elif cmd == "/market":
            symbol = text.split()[1] if len(text.split()) > 1 else "XAUUSD"
            if 'market_data' in self.tools:
                result = self.tools['market_data'].get_ohlcv(symbol.upper(), '1h', 50)
                await self.send_telegram_message(f"<b>Market Data - {symbol.upper()}</b>\n\n{result}")
            else:
                await self.send_telegram_message("Market Data tool not available")

        elif cmd == "/analyze":
            symbol = text.split()[1] if len(text.split()) > 1 else "XAUUSD"
            if 'technical_analysis' in self.tools:
                result = self.tools['technical_analysis'].analyze(symbol.upper(), '1h')
                await self.send_telegram_message(f"<b>Analysis - {symbol.upper()}</b>\n\n{result}")
            else:
                await self.send_telegram_message("Technical Analysis tool not available")

        elif cmd == "/risk":
            if 'risk_officer' in self.tools:
                result = self.tools['risk_officer'].status()
                await self.send_telegram_message(f"<b>Risk Officer Status</b>\n\n{result}")
            else:
                await self.send_telegram_message("Risk Officer tool not available")

        elif cmd == "/strategy":
            symbol = text.split()[1] if len(text.split()) > 1 else "XAUUSD"
            if 'strategy' in self.tools:
                result = self.tools['strategy'].generate_scenarios(symbol.upper())
                await self.send_telegram_message(f"<b>Strategy - {symbol.upper()}</b>\n\n{result}")
            else:
                await self.send_telegram_message("Strategy tool not available")

        elif cmd == "/journal":
            if 'journal' in self.tools:
                result = self.tools['journal'].get_stats()
                await self.send_telegram_message(f"<b>Trade Journal</b>\n\n{result}")
            else:
                await self.send_telegram_message("Journal tool not available")

        elif cmd == "/kill":
            if 'kill_switch' in self.tools:
                result = self.tools['kill_switch'].status()
                await self.send_telegram_message(f"<b>Kill Switch Status</b>\n\n{result}")
            else:
                await self.send_telegram_message("Kill Switch tool not available")

        elif cmd == "/help":
            await self.send_telegram_message(
                "<b>HERMES QUANT OS - Help</b>\n\n"
                "Sistem trading otonom dengan 21 agent.\n"
                "Risk: 0.5%/trade, 1%/day, 3%/week\n\n"
                "<b>Commands:</b>\n"
                "/start - Welcome message\n"
                "/status - System health & PnL\n"
                "/market [SYMBOL] - OHLCV data\n"
                "/analyze [SYMBOL] - SMC Technical Analysis\n"
                "/risk - Risk Officer status\n"
                "/strategy [SYMBOL] - 3 scenarios\n"
                "/journal - Trade stats\n"
                "/kill - Kill switch status\n"
                "/pnl - PnL report\n\n"
                "<b>Tool Calls:</b>\n"
                "[TOOL:market_data]XAUUSD|1h|50[/TOOL]\n"
                "[TOOL:risk_check]XAUUSD|BUY|0.01|2150|2140[/TOOL]\n"
                "[TOOL:strategy]XAUUSD[/TOOL]"
            )

        elif cmd == "/pnl":
            risk_officer = self.tools.get('risk_officer')
            daily_pct = f"{risk_officer.daily_pnl:.2%}" if risk_officer else "0.00%"
            weekly_pct = f"{risk_officer.weekly_pnl:.2%}" if risk_officer else "0.00%"
            await self.send_telegram_message(
                f"<b>PnL Report</b>\n\n"
                f"Daily: {daily_pct}\n"
                f"Weekly: {weekly_pct}\n"
                f"Daily Limit: {RISK_DAILY_MAX:.1%}\n"
                f"Weekly Limit: {RISK_WEEKLY_MAX:.1%}\n"
                f"Trades Today: {len([d for d in self.decisions_log if d.get('type') == 'TRADE' and d.get('timestamp', '')[:10] == datetime.now().strftime('%Y-%m-%d')])}"
            )

        else:
            await self.send_telegram_message(f"Unknown command: {cmd}\nTry /help")

    def get_system_status(self) -> str:
        uptime = datetime.now() - self.start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)

        risk_officer = self.tools.get('risk_officer') if self.tools else None
        daily_pnl_str = f"{risk_officer.daily_pnl:.2%}" if risk_officer else "0.00%"
        weekly_pnl_str = f"{risk_officer.weekly_pnl:.2%}" if risk_officer else "0.00%"

        return (
            f"<b>HERMES QUANT OS STATUS</b>\n\n"
            f"Session: {self.session_id}\n"
            f"Uptime: {hours}h {minutes}m\n"
            f"Provider: {self.current_provider}\n"
            f"Tools: {len(self.tools)}/21\n"
            f"Daily PnL: {daily_pnl_str}\n"
            f"Weekly PnL: {weekly_pnl_str}\n"
            f"Risk: {RISK_MAX_PER_TRADE:.1%}/{RISK_DAILY_MAX:.1%}/{RISK_WEEKLY_MAX:.1%}\n"
            f"Restart Count: {self.restart_count}\n"
            f"Stage: Research Lab (Paper Only)\n"
            f"AGENTS.md: Active"
        )

    async def generate_response(self, prompt: str, force_provider: str = None) -> str:
        import aiohttp

        messages = [
            {"role": "system", "content": AGENTS_SYSTEM_PROMPT},
        ]

        for item in self.conversation_history[-2:]:
            messages.append({"role": "user", "content": item['user']})
            messages.append({"role": "assistant", "content": item['hermes']})

        messages.append({"role": "user", "content": prompt})

        providers_to_try = []

        if force_provider == "nvidia" or force_provider is None:
            if NVIDIA_API_KEY:
                providers_to_try.append(("nvidia", NVIDIA_API_KEY, NVIDIA_API_BASE, MODEL_NAME))

        if force_provider == "groq" or force_provider is None:
            if GROQ_API_KEYS:
                groq_models = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
                for m in groq_models:
                    providers_to_try.append(("groq", self.get_groq_key(), GROQ_API_BASE, m))

        if force_provider == "opencode" or force_provider is None:
            if OPENCODE_API_KEYS:
                providers_to_try.append(("opencode", self.get_opencode_key(), OPENCODE_API_BASE, "opencode"))

        for provider_name, api_key, api_base, model in providers_to_try:
            try:
                logger.info(f"Trying provider: {provider_name} with model: {model}")
                response_text = await self.call_api(api_key, api_base, model, messages)
                self.current_provider = provider_name
                return response_text
            except Exception as e:
                logger.warning(f"{provider_name} failed: {e}")
                continue

        return "Error: All providers failed. System operating in degraded mode."

    async def call_api(self, api_key: str, api_base: str, model: str,
                       messages: list) -> str:
        import aiohttp

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": False
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error = await response.text()
                    raise Exception(f"API error {response.status}: {error[:200]}")

    async def send_telegram_message(self, text: str) -> bool:
        """Send message via Telegram with HTML formatting support"""
        import aiohttp
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        max_length = 4096

        # Use HTML parse mode for rich formatting
        data_base = {"chat_id": TELEGRAM_CHAT_ID, "parse_mode": "HTML"}

        if len(text) > max_length:
            parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            for part in parts:
                data = {**data_base, "text": part}
                try:
                    async with aiohttp.ClientSession() as session:
                        await session.post(url, json=data)
                except Exception as e:
                    logger.error(f"Send error: {e}")
            return True

        data = {**data_base, "text": text}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"Telegram HTML parse failed, falling back to plain: {error_text[:100]}")
                        # Fallback: strip HTML and resend as plain text
                        clean_text = re.sub(r'<[^>]+>', '', text)
                        fallback_data = {"chat_id": TELEGRAM_CHAT_ID, "text": clean_text}
                        async with aiohttp.ClientSession() as session2:
                            async with session2.post(url, json=fallback_data) as response2:
                                return response2.status == 200
                    return True
        except Exception as e:
            logger.error(f"Send telegram error: {e}")
        return False

    async def handle_crash(self, error: Exception) -> None:
        self.restart_count += 1

        self.decisions_log.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'CRASH',
            'error': str(error),
            'restart_count': self.restart_count
        })
        self.save_memory()

        logger.error(f"Crash #{self.restart_count}: {error}")

        if MAX_RESTART_ATTEMPTS > 0 and self.restart_count >= MAX_RESTART_ATTEMPTS:
            logger.critical("Max restart attempts reached!")
            await self.send_telegram_message(
                f"HERMES QUANT OS CRITICAL FAILURE\n\n"
                f"Error: {str(error)[:200]}\n"
                f"Restart attempts: {self.restart_count}/{MAX_RESTART_ATTEMPTS}\n\n"
                f"Manual intervention required!"
            )
            self.running = False
            return

        attempt_info = f"Always-On Mode (Restart #{self.restart_count})"

        await self.send_telegram_message(
            f"HERMES QUANT OS RESTARTING\n\n"
            f"{attempt_info}\n"
            f"Error: {str(error)[:100]}\n"
            f"Restarting in {RESTART_DELAY}s..."
        )

        logger.info(f"Restarting in {RESTART_DELAY} seconds...")
        await asyncio.sleep(RESTART_DELAY)

    def signal_handler(self, signum: int, frame) -> None:
        logger.info("Shutdown signal received!")
        self.decisions_log.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'SHUTDOWN',
            'signal': signum
        })
        self.save_memory()
        self.running = False


async def main():
    hermes = HermesQuantOS()

    signal.signal(signal.SIGINT, hermes.signal_handler)
    signal.signal(signal.SIGTERM, hermes.signal_handler)

    await hermes.start()


if __name__ == "__main__":
    asyncio.run(main())
