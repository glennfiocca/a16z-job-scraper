#!/usr/bin/env python3
"""
Test Workday job filtering logic
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import extract_job_details_advanced

async def test_workday_filtering():
    """Test that Workday jobs are properly filtered out"""
    
    # Test URLs
    test_cases = [
        {
            'url': 'https://rappi.wd12.myworkdayjobs.com/Rappi_jobs/job/COL-Bogot/Marketing-CRM-Automations-Analyst_JR117283',
            'company': 'Rappi',
            'expected': 'FILTERED_OUT'
        },
        {
            'url': 'https://boards.greenhouse.io/spacex/jobs/8114054002',
            'company': 'SpaceX', 
            'expected': 'PROCESSED'
        },
        {
            'url': 'https://stripe.com/jobs/listing/backend-engineer-billing/5932585',
            'company': 'Stripe',
            'expected': 'PROCESSED'
        }
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for i, test_case in enumerate(test_cases, 1):
            try:
                print(f"\n🧪 Test {i}: {test_case['url']}")
                print(f"   Company: {test_case['company']}")
                print(f"   Expected: {test_case['expected']}")
                
                page = await browser.new_page()
                await page.goto(test_case['url'], timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Test the extraction
                result = await extract_job_details_advanced(page, test_case['url'], test_case['company'])
                
                if result is None:
                    print(f"   ✅ RESULT: FILTERED_OUT (as expected)")
                    if test_case['expected'] == 'FILTERED_OUT':
                        print(f"   ✅ SUCCESS: Correctly filtered out Workday job")
                    else:
                        print(f"   ❌ FAILED: Should not have been filtered out")
                else:
                    print(f"   ✅ RESULT: PROCESSED (title: {result.get('title', 'Unknown')})")
                    if test_case['expected'] == 'PROCESSED':
                        print(f"   ✅ SUCCESS: Correctly processed non-Workday job")
                    else:
                        print(f"   ❌ FAILED: Should have been filtered out")
                
                await page.close()
                
            except Exception as e:
                print(f"   💥 ERROR: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_workday_filtering())


