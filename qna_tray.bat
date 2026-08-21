@echo off
rem QNA Tray Launcher — system tray indicator + quick actions
set "PYTHONPATH="
start "" "C:\Python314\pythonw.exe" "%~dp0scripts\qna_tray.py"
echo QNA tray started (check system tray icons).
