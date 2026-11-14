#!/usr/bin/env bash
# xtjson_batch_watch.sh - run the XTJSON Batch app to the end without anyone watching.
#   bash LIB_XTJSON/tools/xtjson_batch_watch.sh [STALL_MINUTES]   (default 5)
# Opens livecode/XTJSON_Batch.livecodescript in the LIB_MCP standalone (port 8767) and
# presses Run. Then it watches XTJSON/batch/_batch_log.tsv: when a stack makes no progress
# for STALL_MINUTES (LiveCode hung or died on it), the standalone is killed and started
# again, and Run carries on: the app marks that stack CRASHED and skips it. Stops at END,
# or after 15 restarts.
HERE="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PROJECTS="$(dirname "$HERE")"
LCMCP="$PROJECTS/LIB_MCP/tools/lcmcp"
LOG="$PROJECTS/XTJSON/batch/_batch_log.tsv"
APP="//wsl\$/Ubuntu${HERE}/livecode/XTJSON_Batch.livecodescript"
STALL=$(( ${1:-5} * 60 ))
EXE=xt3d_MCP.exe

start_run() {
  timeout 120 "$LCMCP" --standalone run "if there is a stack \"XTJSON_Batch\" then delete stack \"XTJSON_Batch\"
go stack \"$APP\"
send \"${BATCH_CMD:-Batch.Run}\" to stack \"XTJSON_Batch\" in 10 milliseconds
return line 1 of field \"Status\" of stack \"XTJSON_Batch\"" 2>&1 | tail -1
}

lines() { [ -f "$LOG" ] && wc -l < "$LOG" || echo 0; }
ended() { [ -f "$LOG" ] && tail -1 "$LOG" | grep -q $'\tEND\t'; }

restarts=0
echo "$(date '+%H:%M') start: $(start_run)"
last=$(lines); idle=0
while true; do
  sleep 15
  if ended; then echo "$(date '+%H:%M') END: $(tail -1 "$LOG" | cut -f4)"; exit 0; fi
  n=$(lines)
  if [ "$n" -ne "$last" ]; then last=$n; idle=0; continue; fi
  idle=$((idle + 15))
  if [ "$idle" -ge "$STALL" ]; then
    restarts=$((restarts + 1))
    stuck=$(tail -1 "$LOG" | cut -f3)
    echo "$(date '+%H:%M') stalled on: $stuck  -> restarting LiveCode ($restarts)"
    [ "$restarts" -gt 15 ] && { echo "too many restarts, giving up"; exit 1; }
    taskkill.exe /IM "$EXE" /F >/dev/null 2>&1
    sleep 5
    echo "$(date '+%H:%M') resume: $(start_run)"
    last=$(lines); idle=0
  fi
done
