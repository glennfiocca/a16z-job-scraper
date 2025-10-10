#!/bin/bash

# Background scraper script that keeps running even if browser is closed

echo "Starting background scraper..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the scraper in the background with nohup
nohup python3 -c "
import asyncio
from main import run_scraper

# Run the scraper
asyncio.run(run_scraper())
" > logs/scraper_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Get the process ID
PID=$!

echo "✅ Scraper started in background with PID: $PID"
echo "📋 View logs in: logs/scraper_*.log"
echo "🛑 To stop: kill $PID"
echo ""
echo "You can now close your browser - the scraper will keep running!"
