@echo off
setlocal enabledelayedexpansion
for %%e in (.py .md .json .yml .yaml .toml .ini .cfg .sh .bat .sql .csv .txt .html .css .js .ts .tsx .jsx .png .svg .ico .lock .env .dockerignore .gitignore .mako .pine .jsonl .cjs .mjs .mako .lock) do (
  set count=0
  for /f %%i in ('dir /s /b /a-d "*%%e" 2^>nul ^| find /v /i "__pycache__" ^| find /v /i "\.git\" ^| find /v /i "\.kilo\" ^| find /v /i "node_modules" ^| find /v /i "\.venv" ^| find /c ""') do set count=%%i
  if !count! gtr 0 echo %%e: !count!
)
