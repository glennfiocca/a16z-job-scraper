#!/usr/bin/env python3
"""
Database cleanup script to remove duplicate jobs
This script identifies and removes duplicate jobs based on multiple criteria
"""

import os
import sys
from datetime import datetime
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import sessionmaker
from models import db, Job, Base
from sqlalchemy import create_engine

def create_app():
    """Create Flask app for database operations"""
    from flask import Flask
    app = Flask(__name__)
    
    # Use the same database URL as the main app
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///jobs.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def normalize_url(url):
    """Normalize URL for consistent deduplication"""
    if not url:
        return url
    
    try:
        from urllib.parse import urlparse, urlunparse, parse_qs
        from urllib.parse import urlencode
        
        # Parse the URL
        parsed = urlparse(url)
        
        # Remove common tracking parameters
        query_params = parse_qs(parsed.query)
        filtered_params = {}
        for key, value in query_params.items():
            if key.lower() not in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'ref', 'source', 'campaign']:
                filtered_params[key] = value
        
        # Rebuild query string
        if filtered_params:
            new_query = urlencode(filtered_params, doseq=True)
        else:
            new_query = ''
        
        # Remove trailing slash from path
        path = parsed.path.rstrip('/')
        
        # Rebuild URL
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            path,
            parsed.params,
            new_query,
            ''  # Remove fragment
        ))
        
        return normalized
    except Exception:
        return url

def find_duplicates_by_url():
    """Find duplicates based on normalized URLs"""
    print("🔍 Finding duplicates by normalized URL...")
    
    # Get all jobs with their normalized URLs
    all_jobs = Job.query.all()
    url_groups = {}
    
    for job in all_jobs:
        if job.source_url:
            normalized = normalize_url(job.source_url)
            if normalized not in url_groups:
                url_groups[normalized] = []
            url_groups[normalized].append(job)
    
    # Find groups with duplicates
    duplicates = {url: jobs for url, jobs in url_groups.items() if len(jobs) > 1}
    
    print(f"📊 Found {len(duplicates)} URL groups with duplicates")
    total_duplicates = sum(len(jobs) - 1 for jobs in duplicates.values())
    print(f"📊 Total duplicate jobs by URL: {total_duplicates}")
    
    return duplicates

def find_duplicates_by_content():
    """Find duplicates based on title + company + location"""
    print("🔍 Finding duplicates by content (title + company + location)...")
    
    # Find jobs with same title, company, and location
    duplicates = db.session.query(
        func.lower(Job.title).label('title'),
        func.lower(Job.company).label('company'),
        func.lower(Job.location).label('location'),
        func.count(Job.id).label('count')
    ).filter(
        Job.title.isnot(None),
        Job.company.isnot(None),
        Job.location.isnot(None)
    ).group_by(
        func.lower(Job.title),
        func.lower(Job.company),
        func.lower(Job.location)
    ).having(
        func.count(Job.id) > 1
    ).all()
    
    print(f"📊 Found {len(duplicates)} content groups with duplicates")
    total_duplicates = sum(row.count - 1 for row in duplicates)
    print(f"📊 Total duplicate jobs by content: {total_duplicates}")
    
    return duplicates

def remove_duplicates_by_url(duplicates, dry_run=True):
    """Remove duplicates, keeping the most recent job"""
    print(f"\n🧹 {'[DRY RUN] ' if dry_run else ''}Removing URL duplicates...")
    
    removed_count = 0
    
    for normalized_url, jobs in duplicates.items():
        if len(jobs) <= 1:
            continue
            
        # Sort by scraped_at (most recent first)
        jobs.sort(key=lambda x: x.scraped_at or datetime.min, reverse=True)
        
        # Keep the first (most recent), remove the rest
        to_remove = jobs[1:]
        
        print(f"  📝 URL: {normalized_url}")
        print(f"     Keeping: {jobs[0].title} at {jobs[0].company} (scraped: {jobs[0].scraped_at})")
        
        for job in to_remove:
            print(f"     Removing: {job.title} at {job.company} (scraped: {job.scraped_at})")
            if not dry_run:
                db.session.delete(job)
            removed_count += 1
    
    if not dry_run:
        db.session.commit()
        print(f"✅ Removed {removed_count} duplicate jobs")
    else:
        print(f"🔍 [DRY RUN] Would remove {removed_count} duplicate jobs")

def remove_duplicates_by_content(duplicates, dry_run=True):
    """Remove content duplicates, keeping the most recent job"""
    print(f"\n🧹 {'[DRY RUN] ' if dry_run else ''}Removing content duplicates...")
    
    removed_count = 0
    
    for row in duplicates:
        title = row.title
        company = row.company
        location = row.location
        
        # Find all jobs with this combination
        jobs = Job.query.filter(
            func.lower(Job.title) == title,
            func.lower(Job.company) == company,
            func.lower(Job.location) == location
        ).all()
        
        if len(jobs) <= 1:
            continue
            
        # Sort by scraped_at (most recent first)
        jobs.sort(key=lambda x: x.scraped_at or datetime.min, reverse=True)
        
        # Keep the first (most recent), remove the rest
        to_remove = jobs[1:]
        
        print(f"  📝 {title} at {company} ({location})")
        print(f"     Keeping: scraped {jobs[0].scraped_at}")
        
        for job in to_remove:
            print(f"     Removing: scraped {job.scraped_at}")
            if not dry_run:
                db.session.delete(job)
            removed_count += 1
    
    if not dry_run:
        db.session.commit()
        print(f"✅ Removed {removed_count} duplicate jobs")
    else:
        print(f"🔍 [DRY RUN] Would remove {removed_count} duplicate jobs")

def main():
    """Main cleanup function"""
    app = create_app()
    
    with app.app_context():
        # Get initial stats
        total_jobs = Job.query.count()
        print(f"📊 Initial job count: {total_jobs}")
        
        # Find and remove URL duplicates
        url_duplicates = find_duplicates_by_url()
        if url_duplicates:
            remove_duplicates_by_url(url_duplicates, dry_run=True)
            
            # Ask for confirmation
            response = input("\n❓ Remove URL duplicates? (y/N): ").strip().lower()
            if response == 'y':
                remove_duplicates_by_url(url_duplicates, dry_run=False)
        
        # Find and remove content duplicates
        content_duplicates = find_duplicates_by_content()
        if content_duplicates:
            remove_duplicates_by_content(content_duplicates, dry_run=True)
            
            # Ask for confirmation
            response = input("\n❓ Remove content duplicates? (y/N): ").strip().lower()
            if response == 'y':
                remove_duplicates_by_content(content_duplicates, dry_run=False)
        
        # Final stats
        final_jobs = Job.query.count()
        print(f"\n📊 Final job count: {final_jobs}")
        print(f"📊 Removed: {total_jobs - final_jobs} duplicate jobs")

if __name__ == "__main__":
    main()
