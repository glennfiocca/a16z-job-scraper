#!/bin/bash

# Stop background scraper

echo "🛑 Stopping background scraper..."

# Find and kill Python scraper processes
PIDS=$(ps aux | grep -E "python.*scraper|run_scraper" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "❌ No scraper processes found"
else
    for PID in $PIDS; do
        echo "Stopping process $PID..."
        kill $PID 2>/dev/null
    done
    echo "✅ Scraper stopped"
fi
