# A16Z Job Scraper

## Overview

A web scraping application designed to collect job listings from the a16z (Andreessen Horowitz) portfolio companies job board. The system uses Playwright for browser automation to navigate job posting websites and extract relevant job information, storing the data in a structured database for analysis and retrieval.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Components

**Web Scraping Engine**
- Built with Playwright for asynchronous browser automation
- Handles headless Chrome browsing for efficient data collection
- Implements robust error handling and timeout management
- Uses a two-phase approach: URL collection followed by individual job processing

**Data Layer**
- SQLAlchemy ORM with Flask integration for database operations
- Job model storing comprehensive job posting information including title, company, location, employment type, description, requirements, and metadata
- Automatic timestamp tracking for scraping activities

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