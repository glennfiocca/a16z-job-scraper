# A16Z Job Scraper

## Overview

A web scraping application designed to collect job listings from the a16z (Andreessen Horowitz) portfolio companies job board. The system uses Playwright for browser automation to navigate job posting websites and extract relevant job information, storing the data in a structured database for analysis and retrieval.

## Running the Scraper

### Option 1: Via Dashboard (Recommended for Quick Runs)
- Open the dashboard at port 5000
- Click "Start Scraping" button
- Keep browser tab open while scraping
- Usually completes in 10-30 minutes

### Option 2: Background Mode (Runs Even When Browser Closed)
Run these commands in the Shell:

**Start background scraper:**
```bash
./run_scraper_background.sh
```

**Check status:**
```bash
./check_scraper_status.sh
```

**Stop scraper:**
```bash
./stop_scraper.sh
```

**View logs:**
```bash
tail -f logs/scraper_*.log
```

The background scraper keeps running even if you close your browser or disconnect from Replit!

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Components

**Web Scraping Engine**
- Built with Playwright for asynchronous browser automation
- Handles headless Chrome browsing for efficient data collection
- Implements robust error handling and timeout management
- Uses a two-phase approach: URL collection followed by individual job processing
- **Smart Resume Feature** (Oct 2025): Automatically skips companies with complete, recent jobs
  - Checks database before scraping each company
  - Skips companies where all jobs are complete (has title, location, employment type, about_job > 200 chars) and recent (< 7 days old)
  - Only re-scrapes companies with incomplete data or stale jobs (7+ days old)
  - Dramatically reduces scraping time and AI costs by avoiding redundant work
  - Shows clear progress: "⏭️ Skipping Company X: all 15 job(s) are complete and recent"
- **AI-First Parsing**: Uses OpenAI GPT-4o-mini (upgraded Oct 2025) as the PRIMARY method to extract structured job data from raw HTML content
  - 60% cheaper than GPT-3.5-turbo with better performance
  - Extracts VERBATIM text from job listings (no summarization or paraphrasing)
  - **Emoji Removal**: All extracted content is cleaned to remove emojis for professional output
  - Extracts comprehensive fields: title, company, about_company, location, about_job (combines description and responsibilities), qualifications, benefits, salary, work environment
  - **Complete Section Extraction**: Captures ENTIRE job sections including all paragraphs and sub-sections
    - About Job field includes ALL content about the role: description, responsibilities, and day-to-day tasks combined
    - This consolidated approach simplifies data capture and avoids confusion between similar fields
    - Increased token limit to 4000 to handle detailed, multi-paragraph job descriptions with responsibilities
  - **Ashby ATS Support**: Special handling for Ashby job boards with explicit emoji section mappings (🚀, 💻, 👋, 🎁)
  - Falls back to manual provider-specific parsing only if AI extraction fails
  - Tracks AI usage metrics: API calls, success rate, fallback frequency, and estimated cost per session
- **US-Only Filter**: Automatically filters out international jobs, only saves US-based positions
  - Checks location against US states, cities, and geographic indicators
  - Rejects jobs with international locations in primary or alternate location fields
  - Conservative approach: skips jobs if location cannot be confirmed as US-based
- **Full-Time & Salaried Only**: Filters out hourly-only positions and non-full-time jobs
  - Employment type standardized to "Full time" for all saved jobs

**Data Layer**
- SQLAlchemy ORM with Flask integration for database operations
- Job model storing comprehensive job posting information including title, company, about_company (company description), location, employment type, about_job (role description and responsibilities combined), qualifications, benefits, and metadata
- Automatic timestamp tracking for scraping activities
- **Recent Schema Update (Oct 2025)**: Consolidated 'description' and 'responsibilities' fields into single 'about_job' field to simplify data capture and reduce AI confusion

**Application Structure**
- Flask application factory pattern for modular configuration
- Environment-based configuration for database connections and secrets
- Database connection pooling with health checks and automatic reconnection

### Design Patterns

**Asynchronous Processing**
- Async/await pattern throughout the scraping pipeline for improved performance
- Browser context management with proper resource cleanup
- Individual page creation for each job to prevent context pollution

**Error Resilience**
- Network timeout handling with configurable timeouts
- Page state waiting mechanisms to ensure complete content loading
- Provider-specific element waiting for different job board platforms

## External Dependencies

**Browser Automation**
- Playwright: Headless browser control and web page interaction
- Chromium: Browser engine for rendering and content extraction

**Web Framework**
- Flask: Lightweight web application framework
- Flask-SQLAlchemy: Database ORM integration

**Database**
- SQLAlchemy: Database abstraction layer with connection pooling
- Database URI configurable via environment variables (supports various SQL databases)

**Infrastructure**
- Environment variable configuration for secrets and database connections
- UTC datetime handling for consistent timestamp management