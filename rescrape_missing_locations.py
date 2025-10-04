#!/usr/bin/env python3
"""
Re-scrape jobs with missing locations to apply the Greenhouse fix
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Job
from playwright.async_api import async_playwright
from main import extract_greenhouse_job, extract_job_details_advanced
from datetime import datetime
import time

async def rescrape_missing_locations(limit=50, dry_run=True):
    """
    Re-scrape jobs with missing locations to apply the Greenhouse fix
    
    Args:
        limit: Maximum number of jobs to re-scrape (for testing)
        dry_run: If True, only show what would be updated without making changes
    """
    app = create_app()
    
    with app.app_context():
        print("🔄 RE-SCRAPING MISSING LOCATIONS")
        print("=" * 50)
        
        # Find jobs with missing locations from Greenhouse
        missing_location_jobs = db.session.execute(db.text("""
            SELECT id, url, company, title, location
            FROM jobs 
            WHERE (location IS NULL OR location = '' OR location = 'NULL')
            AND url LIKE '%greenhouse%'
            ORDER BY company, id
            LIMIT :limit
        """), {'limit': limit}).fetchall()
        
        print(f"📊 Found {len(missing_location_jobs)} jobs with missing locations")
        
        if dry_run:
            print(f"🧪 DRY RUN MODE - No changes will be made")
            print(f"📋 Jobs that would be re-scraped:")
            for job in missing_location_jobs[:10]:  # Show first 10
                print(f"   • {job.company}: {job.title}")
            if len(missing_location_jobs) > 10:
                print(f"   ... and {len(missing_location_jobs) - 10} more")
            return
        
        # Start re-scraping
        print(f"🚀 Starting re-scraping process...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            success_count = 0
            error_count = 0
            
            for i, job in enumerate(missing_location_jobs, 1):
                try:
                    print(f"\n🔄 Processing {i}/{len(missing_location_jobs)}: {job.company} - {job.title}")
                    
                    page = await browser.new_page()
                    
                    # Navigate to the job URL
                    await page.goto(job.source_url, timeout=30000)
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # Extract job data using the fixed Greenhouse extraction
                    job_data = {'source_url': job.source_url, 'company': job.company}
                    
                    if 'greenhouse' in job.source_url.lower():
                        result = await extract_greenhouse_job(page, job_data)
                    else:
                        result = await extract_job_details_advanced(page, job.source_url, job.company)
                    
                    # Check if we got a location
                    new_location = result.get('location')
                    
                    if new_location and new_location.strip():
                        # Update the database using raw SQL to avoid schema issues
                        try:
                            db.session.execute(db.text("""
                                UPDATE jobs 
                                SET location = :location, scraped_at = :scraped_at
                                WHERE id = :job_id
                            """), {
                                'location': new_location.strip(),
                                'scraped_at': datetime.utcnow(),
                                'job_id': job.id
                            })
                            db.session.commit()
                            
                            print(f"   ✅ Updated location: '{new_location}'")
                            success_count += 1
                        except Exception as db_error:
                            print(f"   ❌ Database error: {db_error}")
                            db.session.rollback()
                            error_count += 1
                    else:
                        print(f"   ⚠️  No location found in re-scrape")
                        error_count += 1
                    
                    await page.close()
                    
                    # Small delay to be respectful
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"   ❌ Error processing {job.source_url}: {e}")
                    error_count += 1
                    
                    try:
                        await page.close()
                    except:
                        pass
            
            await browser.close()
            
            # Summary
            print(f"\n📊 RE-SCRAPING SUMMARY")
            print("=" * 30)
            print(f"✅ Successfully updated: {success_count}")
            print(f"❌ Errors/Failures: {error_count}")
            print(f"📈 Success rate: {(success_count/(success_count+error_count)*100):.1f}%")
            
            if success_count > 0:
                print(f"\n🎉 SUCCESS! {success_count} jobs now have locations!")
            else:
                print(f"\n⚠️  No jobs were successfully updated")

async def test_rescrape_sample():
    """Test the re-scraping on a small sample"""
    print("🧪 TESTING RE-SCRAPING ON SAMPLE")
    print("=" * 40)
    
    # First, show what would be updated
    await rescrape_missing_locations(limit=5, dry_run=True)
    
    print(f"\n🚀 Running actual test on 3 jobs...")
    await rescrape_missing_locations(limit=3, dry_run=False)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Re-scrape jobs with missing locations')
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of jobs to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    parser.add_argument('--test', action='store_true', help='Run test on small sample')
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_rescrape_sample())
    else:
        asyncio.run(rescrape_missing_locations(limit=args.limit, dry_run=args.dry_run))
