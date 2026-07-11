#!/bin/bash
cd /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree
nohup python3.12 -m quant_nanggroe.live_engine start > logs/engine.log 2>&1 &
PID=$!
echo $PID > /tmp/qna_engine.pid
echo "Engine started with PID $PID"
