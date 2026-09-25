#!/bin/bash
# Daily Curio digest — Mon through Sat.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/curio_$(date +%Y-%m-%d).log"

echo "" >> "$LOG_FILE"
echo "============================================================" >> "$LOG_FILE"
echo "CURIO DAILY — $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$LOG_FILE"
echo "============================================================" >> "$LOG_FILE"

if ! command -v uv &> /dev/null; then
    echo "Error: uv not on PATH" >> "$LOG_FILE"
    exit 1
fi

uv run curio --mode daily >> "$LOG_FILE" 2>&1
STATUS=$?

if [ $STATUS -eq 0 ]; then
    echo "" >> "$LOG_FILE"
    echo "Curio daily completed successfully." >> "$LOG_FILE"
else
    echo "" >> "$LOG_FILE"
    echo "ERROR: Curio daily exited $STATUS" >> "$LOG_FILE"
fi

echo "============================================================" >> "$LOG_FILE"
exit $STATUS
