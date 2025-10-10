#!/bin/bash

# Check if scraper is running

echo "🔍 Checking scraper status..."
echo ""

# Check for Python scraper processes
SCRAPERS=$(ps aux | grep -E "python.*scraper|run_scraper" | grep -v grep)

if [ -z "$SCRAPERS" ]; then
    echo "❌ No scraper is currently running"
else
    echo "✅ Scraper is running:"
    echo "$SCRAPERS"
    echo ""
    echo "📋 Recent logs:"
    if [ -d "logs" ]; then
        LATEST_LOG=$(ls -t logs/scraper_*.log 2>/dev/null | head -1)
        if [ -n "$LATEST_LOG" ]; then
            echo "Latest log: $LATEST_LOG"
            echo "---"
            tail -20 "$LATEST_LOG"
        fi
    fi
fi

echo ""
echo "💾 Database status:"
python3 -c "
from app import app, db
from models import Job

with app.app_context():
    total_jobs = Job.query.count()
    companies = db.session.query(Job.company).distinct().count()
    print(f'   Total jobs: {total_jobs}')
    print(f'   Unique companies: {companies}')
"
