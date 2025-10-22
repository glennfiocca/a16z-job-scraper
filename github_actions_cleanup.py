#!/usr/bin/env python3
"""
GitHub Actions cleanup script
Runs analysis and cleanup automatically for CI/CD
"""

import os
import sys
from datetime import datetime
from sqlalchemy import func
from models import db, Job
from flask import Flask

def create_app():
    """Create Flask app for database operations"""
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

def analyze_and_cleanup():
    """Analyze database and clean up duplicates"""
    print("🔍 GITHUB ACTIONS CLEANUP")
    print("=" * 40)
    
    # Get initial stats
    total_jobs = Job.query.count()
    print(f"📊 Initial job count: {total_jobs:,}")
    
    # Find content duplicates
    content_duplicates = db.session.query(
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
    
    total_content_duplicates = sum(row.count - 1 for row in content_duplicates)
    print(f"📊 Content duplicates found: {total_content_duplicates}")
    
    # Remove duplicates
    removed_count = 0
    
    for row in content_duplicates:
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
        
        for job in to_remove:
            db.session.delete(job)
            removed_count += 1
    
    if removed_count > 0:
        db.session.commit()
        print(f"✅ Removed {removed_count} duplicate jobs")
    else:
        print("✅ No duplicates found")
    
    # Final stats
    final_jobs = Job.query.count()
    print(f"📊 Final job count: {final_jobs:,}")
    
    # Show top companies
    companies = db.session.query(
        Job.company, 
        func.count(Job.id).label('count')
    ).filter(
        Job.company.isnot(None)
    ).group_by(Job.company).order_by(
        func.count(Job.id).desc()
    ).limit(5).all()
    
    print(f"\n🏢 Top 5 companies:")
    for company, count in companies:
        print(f"   {company}: {count:,} jobs")
    
    return removed_count

def main():
    """Main function for GitHub Actions"""
    app = create_app()
    
    with app.app_context():
        try:
            removed = analyze_and_cleanup()
            print(f"\n🎉 Cleanup completed successfully! Removed {removed} duplicates.")
            return 0
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            return 1

if __name__ == "__main__":
    sys.exit(main())
