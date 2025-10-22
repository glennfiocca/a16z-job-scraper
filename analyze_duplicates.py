#!/usr/bin/env python3
"""
Analyze database for duplicate jobs and provide statistics
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

def analyze_database():
    """Analyze the database for duplicates and provide statistics"""
    print("🔍 ANALYZING DATABASE FOR DUPLICATES")
    print("=" * 50)
    
    # Basic stats
    total_jobs = Job.query.count()
    print(f"📊 Total jobs in database: {total_jobs:,}")
    
    # Jobs by company
    companies = db.session.query(
        Job.company, 
        func.count(Job.id).label('count')
    ).filter(
        Job.company.isnot(None)
    ).group_by(Job.company).order_by(
        func.count(Job.id).desc()
    ).limit(10).all()
    
    print(f"\n🏢 Top 10 companies by job count:")
    for company, count in companies:
        print(f"   {company}: {count:,} jobs")
    
    # Jobs by source
    sources = db.session.query(
        Job.source, 
        func.count(Job.id).label('count')
    ).filter(
        Job.source.isnot(None)
    ).group_by(Job.source).order_by(
        func.count(Job.id).desc()
    ).all()
    
    print(f"\n📱 Jobs by source platform:")
    for source, count in sources:
        print(f"   {source}: {count:,} jobs")
    
    # URL duplicates analysis
    print(f"\n🔗 URL DUPLICATES ANALYSIS:")
    
    # Get all jobs with URLs
    jobs_with_urls = Job.query.filter(Job.source_url.isnot(None)).all()
    url_groups = {}
    
    for job in jobs_with_urls:
        normalized = normalize_url(job.source_url)
        if normalized not in url_groups:
            url_groups[normalized] = []
        url_groups[normalized].append(job)
    
    # Find duplicates
    url_duplicates = {url: jobs for url, jobs in url_groups.items() if len(jobs) > 1}
    total_url_duplicates = sum(len(jobs) - 1 for jobs in url_duplicates.values())
    
    print(f"   Jobs with URLs: {len(jobs_with_urls):,}")
    print(f"   Unique normalized URLs: {len(url_groups):,}")
    print(f"   URL groups with duplicates: {len(url_duplicates):,}")
    print(f"   Total URL duplicates: {total_url_duplicates:,}")
    
    # Show worst URL duplicates
    if url_duplicates:
        worst_urls = sorted(url_duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        print(f"\n   🚨 Worst URL duplicates:")
        for url, jobs in worst_urls:
            print(f"      {url}: {len(jobs)} copies")
            for job in jobs[:3]:  # Show first 3
                print(f"         - {job.title} at {job.company} (scraped: {job.scraped_at})")
            if len(jobs) > 3:
                print(f"         ... and {len(jobs) - 3} more")
    
    # Content duplicates analysis
    print(f"\n📝 CONTENT DUPLICATES ANALYSIS:")
    
    # Find jobs with same title + company + location
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
    ).order_by(
        func.count(Job.id).desc()
    ).all()
    
    total_content_duplicates = sum(row.count - 1 for row in content_duplicates)
    
    print(f"   Content groups with duplicates: {len(content_duplicates):,}")
    print(f"   Total content duplicates: {total_content_duplicates:,}")
    
    # Show worst content duplicates
    if content_duplicates:
        print(f"\n   🚨 Worst content duplicates:")
        for row in content_duplicates[:5]:
            print(f"      '{row.title}' at {row.company} ({row.location}): {row.count} copies")
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   Total jobs: {total_jobs:,}")
    print(f"   URL duplicates: {total_url_duplicates:,}")
    print(f"   Content duplicates: {total_content_duplicates:,}")
    print(f"   Estimated unique jobs: {total_jobs - total_url_duplicates - total_content_duplicates:,}")
    
    # Recent activity
    recent_jobs = Job.query.order_by(Job.scraped_at.desc()).limit(5).all()
    print(f"\n⏰ Most recent jobs:")
    for job in recent_jobs:
        print(f"   {job.title} at {job.company} (scraped: {job.scraped_at})")

def main():
    """Main analysis function"""
    app = create_app()
    
    with app.app_context():
        analyze_database()

if __name__ == "__main__":
    main()
