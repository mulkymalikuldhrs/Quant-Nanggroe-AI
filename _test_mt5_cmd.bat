@echo off
cd /d D:\repositories\Quant-Nanggroe-AI-worktree
set QNAI_MT5_ACCOUNTS=[{"login":372044706,"password":"@15September","server":"ValetaxIntl_Live-2","role":"primary"}]
.venv\Scripts\python.exe -c "import MetaTrader5 as mt5, json, os, sys; acc = json.loads(os.environ['QNAI_MT5_ACCOUNTS'])[0]; print('Connecting to', acc['server'], 'login', acc['login']); sys.stdout.flush(); r = mt5.initialize(login=acc['login'], password=acc['password'], server=acc['server']); print('Init result:', r, 'Error:', mt5.last_error()); sys.stdout.flush(); mt5.shutdown(); print('DONE')"
pause
