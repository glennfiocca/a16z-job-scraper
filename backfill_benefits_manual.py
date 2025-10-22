#!/usr/bin/env python3
"""
Backfill benefits data for specific job URLs.
Use this if you need to manually provide a list of job URLs to re-scrape.
"""

import asyncio
import requests
import json
from playwright.async_api import async_playwright
from main import extract_job_details_advanced, wait_for_provider_elements

# Pipeline API Configuration
PIPELINE_API_URL = "https://atpipeline.com"
PIPELINE_API_KEY = "sPqH575yX54u1x72G2sLoUhc18nsqUJcqnMq3cYR"

# Manual list of job URLs to re-scrape (add your URLs here)
JOB_URLS_TO_RESCAPE = [
    # Example URLs - replace with actual job URLs from your Pipeline database
    # "https://boards.greenhouse.io/company1/jobs/123456",
    # "https://boards.greenhouse.io/company2/jobs/789012",
    # Add more URLs as needed
]

async def rescrape_job_for_benefits(job_url, company_name=None):
    """Re-scrape a single job URL to extract benefits information"""
    try:
        print(f"🔍 Re-scraping: {job_url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(job_url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Wait for provider-specific elements
            await wait_for_provider_elements(page, job_url)
            
            # Extract job details (this will include benefits)
            job_data = await extract_job_details_advanced(page, job_url, company_name or "Unknown")
            
            await browser.close()
            
            if job_data and job_data.get('benefits'):
                return {
                    'benefits': job_data.get('benefits'),
                    'title': job_data.get('title'),
                    'company': job_data.get('company')
                }
            else:
                return None
                
    except Exception as e:
        print(f"❌ Error re-scraping {job_url}: {e}")
        return None

def send_benefits_update_to_pipeline(job_url, benefits_data, title, company):
    """Send benefits update to Pipeline API"""
    try:
        # Create a job update payload
        job_update = {
            'sourceUrl': job_url,
            'benefits': benefits_data,
            'title': title,
            'company': company
        }
        
        response = requests.post(
            f"{PIPELINE_API_URL}/api/webhook/jobs/update",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': PIPELINE_API_KEY
            },
            json={'jobs': [job_update], 'source': 'Benefits Backfill'}
        )
        
        if response.status_code == 200:
            print(f"✅ Successfully updated benefits for: {title} at {company}")
            return True
        else:
            print(f"❌ Failed to update benefits: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating benefits: {e}")
        return False

async def backfill_benefits_manual(dry_run=True):
    """Main function to backfill benefits for manually specified job URLs"""
    print(f"🔄 Starting manual benefits backfill (dry_run: {dry_run})")
    
    if not JOB_URLS_TO_RESCAPE:
        print("❌ No job URLs specified in JOB_URLS_TO_RESCAPE list")
        print("💡 Add job URLs to the JOB_URLS_TO_RESCAPE list in this script")
        return
    
    print(f"📋 Found {len(JOB_URLS_TO_RESCAPE)} job URLs to process")
    
    success_count = 0
    error_count = 0
    
    for i, job_url in enumerate(JOB_URLS_TO_RESCAPE, 1):
        print(f"\n🔍 Processing job {i}/{len(JOB_URLS_TO_RESCAPE)}")
        
        # Re-scrape for benefits
        result = await rescrape_job_for_benefits(job_url)
        
        if result and result.get('benefits'):
            benefits_data = result['benefits']
            title = result['title']
            company = result['company']
            
            print(f"   ✅ Found benefits: {len(benefits_data)} characters")
            print(f"   📝 Preview: {benefits_data[:100]}...")
            
            if not dry_run:
                # Send update to Pipeline API
                if send_benefits_update_to_pipeline(job_url, benefits_data, title, company):
                    success_count += 1
                else:
                    error_count += 1
            else:
                print(f"   🔍 DRY RUN: Would update benefits for {title} at {company}")
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
    dry_run = True
    
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'false':
        dry_run = False
    
    print(f"🚀 Starting manual benefits backfill...")
    print(f"   Dry run: {dry_run}")
    print(f"   Job URLs: {len(JOB_URLS_TO_RESCAPE)}")
    
    asyncio.run(backfill_benefits_manual(dry_run))






