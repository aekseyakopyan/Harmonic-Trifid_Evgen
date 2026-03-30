#!/bin/bash
# start_alexey.sh - Script to start/restart the Alexey userbot in the background

cd /opt/harmonic-trifid/Harmonic-Trifid_Evgen
export PYTHONPATH=.

echo "--- Restarting Alexey ---"
# Find existing PIDs for the Alexey process
PIDS=$(pgrep -f "systems/alexey/main.py")
if [ -n "$PIDS" ]; then
    echo "Killing existing PIDs: $PIDS"
    for PID in $PIDS; do
        if [ "$PID" != "$$" ]; then
            kill -9 "$PID" 2>/dev/null
        fi
    done
fi

# Ensure log and pid directories exist
mkdir -p logs pids

# Rotate logs if they get too large (optional but good practice)
if [ -f "logs/alexey.log" ] && [ $(stat -c%s "logs/alexey.log") -gt 10000000 ]; then
    mv logs/alexey.log logs/alexey.log.old
fi

# Start the process with unbuffered output
nohup ./venv/bin/python3 -u systems/alexey/main.py >> logs/alexey.log 2>&1 &
NEW_PID=$!
echo $NEW_PID > pids/alexey.pid

echo "Alexey started with PID: $NEW_PID"
echo "Logs are being written to logs/alexey.log"
sleep 5
# Check if it's still running
if ps -p $NEW_PID > /dev/null; then
    echo "Process is running successfully."
else
    echo "ERROR: Process failed to start. Check logs/alexey.log for details."
    tail -n 20 logs/alexey.log
fi
