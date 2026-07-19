#!/usr/bin/env python3
"""Patch qna_prod.py to wire in ProtectionEngine, BrokerPacks, Council Integration."""
import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'quant_nanggroe/qna_prod.py'
data = open(path).read()

old_start = '    def _init_engines(self) -> None:'
old_end = '            self._smc_engine = None'

start = data.find(old_start)
end = data.find(old_end, start) + len(old_end)
old_block = data[start:end]

new_imports = (
    '            from quant_nanggroe.engine.execution.protection import ProtectionEngine\n'
    '            from quant_nanggroe.exchange.broker_pack import TradingMode, get_registry'
)

new_body = (
    '            self._protection_engine = ProtectionEngine(intrabar_mode="balanced")\n'
    '            self._broker_registry = get_registry()\n'
    '            self._trading_mode = TradingMode()\n'
    '            logger.info("BrokerPacks: %d registered, mode=%s",\n'
    '                        len(self._broker_registry.list_packs()),\n'
    '                        self._trading_mode.mode)\n'
    '            try:\n'
    '                from quant_nanggroe.engine.council_integration import integrate_council_findings\n'
    '                asyncio.create_task(self._run_council_integration())\n'
    '            except ImportError:\n'
    '                pass'
)

old_block_new = old_block.replace(
    'from quant_nanggroe.engine.risk.sizing import calculate_position_size',
    'from quant_nanggroe.engine.risk.sizing import calculate_position_size\n' + new_imports
)
old_block_new = old_block_new.replace(
    '            self._risk_gate = ConstitutionalRiskGuard()',
    '            self._risk_gate = ConstitutionalRiskGuard()\n' + new_body
)
old_block_new = old_block_new.replace(
    'logger.info("Engines initialized: SMC, Risk, Killzone")',
    'logger.info("Engines initialized: SMC, Risk, Killzone, Protection, BrokerPacks")'
)

data = data.replace(old_block, old_block_new)

council_method = (
    '\n'
    '    async def _run_council_integration(self) -> None:\n'
    '        """Run council integration findings asynchronously at startup."""\n'
    '        try:\n'
    '            from quant_nanggroe.engine.council_integration import integrate_council_findings\n'
    '            result = await integrate_council_findings()\n'
    '            logger.info("Council integration: HF=%d rules, QNA=%d packs, SKILLS=%d pending",\n'
    '                        result["wave1_hf"]["rules_added"],\n'
    '                        result["wave2_qna"]["packs_registered"],\n'
    '                        result["wave3_skills"]["pending_algorithms"])\n'
    '        except Exception as e:\n'
    '            logger.warning(f"Council integration skipped: {e}")\n'
)

insert_marker = '            self._smc_engine = None\n\n'
insert_pos = data.find(insert_marker, end) + len(insert_marker)
data = data[:insert_pos] + council_method + data[insert_pos:]

open(path, 'w').write(data)
print('PATCHED OK')
