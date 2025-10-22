#!/usr/bin/env python3
"""
Automated database cleanup script to remove duplicate jobs
This version runs without user interaction for GitHub Actions
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

def remove_duplicates_by_content(dry_run=False):
    """Remove content duplicates, keeping the most recent job"""
    print(f"🧹 {'[DRY RUN] ' if dry_run else ''}Removing content duplicates...")
    
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
    
    return removed_count

def main():
    """Main cleanup function"""
    app = create_app()
    
    with app.app_context():
        # Get initial stats
        total_jobs = Job.query.count()
        print(f"📊 Initial job count: {total_jobs}")
        
        # Remove content duplicates automatically
        removed_count = remove_duplicates_by_content(dry_run=False)
        
        # Final stats
        final_jobs = Job.query.count()
        print(f"\n📊 Final job count: {final_jobs}")
        print(f"📊 Removed: {total_jobs - final_jobs} duplicate jobs")
        
        return removed_count

if __name__ == "__main__":
    main()
