@echo off
cd /d D:\repositories\Quant-Nanggroe-AI-worktree
.venv\Scripts\python.exe -c "import MetaTrader5 as mt5; print('Import OK'); r = mt5.initialize(timeout=15000); print('Init result:', r, 'Error:', mt5.last_error()); mt5.shutdown(); print('DONE')"
pause
