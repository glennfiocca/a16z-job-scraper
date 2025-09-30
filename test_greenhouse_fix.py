#!/usr/bin/env python3
"""
Test the updated Greenhouse location extraction
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import extract_greenhouse_job

async def test_greenhouse_location():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Test the specific Greenhouse URL
            url = "https://job-boards.greenhouse.io/waymark/jobs/4609499005"
            print(f"🧪 Testing location extraction for: {url}")
            
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Test the updated extraction
            job_data = {'url': url, 'company': 'Waymark'}
            result = await extract_greenhouse_job(page, job_data)
            
            print(f"\n📊 Results:")
            print(f"   Title: {result.get('title', 'Not found')}")
            print(f"   Company: {result.get('company', 'Not found')}")
            print(f"   Location: {result.get('location', 'Not found')}")
            print(f"   Employment Type: {result.get('employment_type', 'Not found')}")
            
            if result.get('location'):
                print(f"\n✅ SUCCESS: Location extracted as '{result['location']}'")
            else:
                print(f"\n❌ FAILED: No location found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_greenhouse_location())


