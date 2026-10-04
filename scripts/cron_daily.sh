#!/bin/bash
# Daily Curio digest — Mon through Sat.

# No `set -e`: we want to reach the status footer even when curio fails.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR" || exit 1

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/curio_$(date +%Y-%m-%d).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] [cron_daily] $*" >> "$LOG_FILE"
}

echo "" >> "$LOG_FILE"
echo "============================================================" >> "$LOG_FILE"
echo "CURIO DAILY — $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$LOG_FILE"
echo "============================================================" >> "$LOG_FILE"

log "Cron triggered (pid $$, user $(whoami))"
log "Project dir: $PROJECT_DIR"
log "PATH: $PATH"

if ! command -v uv &> /dev/null; then
    log "ERROR: uv not on PATH — aborting"
    exit 1
fi
log "Using uv at $(command -v uv)"

START_TS=$(date +%s)
log "Starting: uv run curio --mode daily"

uv run curio --mode daily >> "$LOG_FILE" 2>&1
STATUS=$?

ELAPSED=$(( $(date +%s) - START_TS ))
echo "" >> "$LOG_FILE"
if [ $STATUS -eq 0 ]; then
    log "Curio daily completed successfully in ${ELAPSED}s."
else
    log "ERROR: Curio daily exited $STATUS after ${ELAPSED}s."
fi

echo "============================================================" >> "$LOG_FILE"
exit $STATUS
