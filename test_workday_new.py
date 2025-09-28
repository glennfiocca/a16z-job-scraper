#!/usr/bin/env python3
"""
Test the new Workday extraction logic
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import extract_workday_job

async def test_workday_new():
    """Test the new Workday extraction logic"""
    
    # Test URL from the database
    test_url = "https://rappi.wd12.myworkdayjobs.com/Rappi_jobs/job/COL-Bogot/Marketing-CRM-Automations-Analyst_JR117283"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print(f"🧪 Testing new Workday extraction: {test_url}")
            
            await page.goto(test_url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Test the new extraction logic
            job_data = {'url': test_url, 'company': 'Rappi'}
            result = await extract_workday_job(page, job_data)
            
            print(f"\n📊 Extraction Results:")
            print(f"   Title: {result.get('title', 'NOT FOUND')}")
            print(f"   Company: {result.get('company', 'NOT FOUND')}")
            print(f"   Location: {result.get('location', 'NOT FOUND')}")
            print(f"   Employment Type: {result.get('employment_type', 'NOT FOUND')}")
            print(f"   Job ID: {result.get('job_id', 'NOT FOUND')}")
            print(f"   Description: {len(result.get('description', ''))} characters")
            
            # Check if extraction was successful
            success = (
                result.get('title') and result.get('title') != 'NOT FOUND' and
                result.get('location') and result.get('location') != 'NOT FOUND' and
                result.get('employment_type') and result.get('employment_type') != 'NOT FOUND' and
                len(result.get('description', '')) > 1000
            )
            
            if success:
                print(f"\n✅ SUCCESS: Workday extraction is working!")
            else:
                print(f"\n❌ FAILED: Workday extraction needs improvement")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_workday_new())
