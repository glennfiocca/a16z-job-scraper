#!/usr/bin/env python3
"""
Comprehensive test of Greenhouse location extraction fix
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import extract_greenhouse_job

async def test_multiple_greenhouse_jobs():
    """Test location extraction on multiple Greenhouse job URLs"""
    
    # Sample Greenhouse URLs from your database
    test_urls = [
        "https://job-boards.greenhouse.io/waymark/jobs/4609499005",  # Remote
        "https://boards.greenhouse.io/spacex/jobs/8114054002",        # SpaceX
        "https://boards.greenhouse.io/appliedintuition/jobs/4607788005",  # Applied Intuition
        "https://job-boards.greenhouse.io/labelbox/jobs/4915531007",  # Labelbox
        "https://boards.greenhouse.io/benchling/jobs/7246942",       # Benchling
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        results = []
        
        for i, url in enumerate(test_urls, 1):
            try:
                page = await browser.new_page()
                print(f"\n🧪 Test {i}/{len(test_urls)}: {url}")
                
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Extract company name from URL
                company_name = url.split('/')[-3] if 'greenhouse.io' in url else 'Unknown'
                
                # Test the updated extraction
                job_data = {'url': url, 'company': company_name}
                result = await extract_greenhouse_job(page, job_data)
                
                location = result.get('location', 'NULL')
                title = result.get('title', 'Unknown Title')
                
                print(f"   📍 Location: {location}")
                print(f"   📝 Title: {title}")
                
                if location and location != 'NULL':
                    print(f"   ✅ SUCCESS: Location extracted")
                    results.append({'url': url, 'location': location, 'title': title, 'status': 'SUCCESS'})
                else:
                    print(f"   ❌ FAILED: No location found")
                    results.append({'url': url, 'location': location, 'title': title, 'status': 'FAILED'})
                
                await page.close()
                
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                results.append({'url': url, 'location': 'ERROR', 'title': 'ERROR', 'status': 'ERROR'})
        
        await browser.close()
        
        # Summary
        print(f"\n📊 Test Results Summary:")
        print(f"=" * 50)
        
        success_count = len([r for r in results if r['status'] == 'SUCCESS'])
        failed_count = len([r for r in results if r['status'] == 'FAILED'])
        error_count = len([r for r in results if r['status'] == 'ERROR'])
        
        print(f"✅ Successful extractions: {success_count}")
        print(f"❌ Failed extractions: {failed_count}")
        print(f"💥 Errors: {error_count}")
        print(f"📈 Success rate: {(success_count/len(results)*100):.1f}%")
        
        if success_count > 0:
            print(f"\n🎉 SUCCESS! Location extraction is working!")
            print(f"📍 Sample locations found:")
            for result in results:
                if result['status'] == 'SUCCESS':
                    print(f"   • {result['title']}: {result['location']}")
        else:
            print(f"\n❌ ISSUE: No locations were extracted successfully")
        
        return results

if __name__ == "__main__":
    asyncio.run(test_multiple_greenhouse_jobs())

