#!/usr/bin/env python3
"""
Backfill benefits data for existing jobs in Pipeline database.
This script will re-scrape job URLs to extract benefits information.
"""

import asyncio
import requests
import json
from playwright.async_api import async_playwright
from ai_parser import AIParser
from main import extract_job_details_advanced, wait_for_provider_elements

# Pipeline API Configuration
PIPELINE_API_URL = "https://atpipeline.com"
PIPELINE_API_KEY = "sPqH575yX54u1x72G2sLoUhc18nsqUJcqnMq3cYR"

async def get_existing_jobs_without_benefits(limit=50):
    """Get existing jobs from Pipeline API that don't have benefits data"""
    try:
        # This would need to be adjusted based on your Pipeline API's actual endpoints
        # You might need to check what endpoints are available for querying existing jobs
        response = requests.get(
            f"{PIPELINE_API_URL}/api/jobs",
            headers={'X-API-Key': PIPELINE_API_KEY},
            params={'limit': limit, 'missing_benefits': True}  # Hypothetical parameter
        )
        
        if response.status_code == 200:
            return response.json().get('jobs', [])
        else:
            print(f"❌ Failed to fetch existing jobs: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error fetching existing jobs: {e}")
        return []

async def rescrape_job_for_benefits(job_url, company_name):
    """Re-scrape a single job URL to extract benefits information"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(job_url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Wait for provider-specific elements
            await wait_for_provider_elements(page, job_url)
            
            # Extract job details (this will include benefits)
            job_data = await extract_job_details_advanced(page, job_url, company_name)
            
            await browser.close()
            
            if job_data and job_data.get('benefits'):
                return job_data.get('benefits')
            else:
                return None
                
    except Exception as e:
        print(f"❌ Error re-scraping {job_url}: {e}")
        return None

def update_job_benefits(job_id, benefits_data):
    """Update a job in Pipeline API with benefits data"""
    try:
        response = requests.patch(
            f"{PIPELINE_API_URL}/api/jobs/{job_id}",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': PIPELINE_API_KEY
            },
            json={'benefits': benefits_data}
        )
        
        if response.status_code == 200:
            print(f"✅ Updated job {job_id} with benefits data")
            return True
        else:
            print(f"❌ Failed to update job {job_id}: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating job {job_id}: {e}")
        return False

async def backfill_benefits(limit=50, dry_run=True):
    """Main function to backfill benefits for existing jobs"""
    print(f"🔄 Starting benefits backfill (limit: {limit}, dry_run: {dry_run})")
    
    # Get existing jobs without benefits
    existing_jobs = await get_existing_jobs_without_benefits(limit)
    
    if not existing_jobs:
        print("❌ No existing jobs found or API endpoint not available")
        print("💡 You may need to manually provide a list of job URLs to re-scrape")
        return
    
    print(f"📋 Found {len(existing_jobs)} jobs to process")
    
    success_count = 0
    error_count = 0
    
    for i, job in enumerate(existing_jobs, 1):
        job_url = job.get('sourceUrl')
        job_id = job.get('id')
        company_name = job.get('company', 'Unknown')
        
        if not job_url:
            print(f"⏭️  Skipping job {i}: No source URL")
            continue
            
        print(f"\n🔍 Processing job {i}/{len(existing_jobs)}: {job.get('title', 'Unknown Title')}")
        print(f"   URL: {job_url}")
        
        # Re-scrape for benefits
        benefits_data = await rescrape_job_for_benefits(job_url, company_name)
        
        if benefits_data:
            print(f"   ✅ Found benefits: {len(benefits_data)} characters")
            
            if not dry_run:
                # Update the job in Pipeline API
                if update_job_benefits(job_id, benefits_data):
                    success_count += 1
                else:
                    error_count += 1
            else:
                print(f"   🔍 DRY RUN: Would update job {job_id}")
                success_count += 1
        else:
            print(f"   ❌ No benefits found")
            error_count += 1
    
    print(f"\n📊 Backfill Summary:")
    print(f"   ✅ Successfully processed: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   🔍 Dry run: {dry_run}")

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    limit = 50
    dry_run = True
    
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2].lower() == 'false':
        dry_run = False
    
    print(f"🚀 Starting benefits backfill...")
    print(f"   Limit: {limit}")
    print(f"   Dry run: {dry_run}")
    
    asyncio.run(backfill_benefits(limit, dry_run))







