#!/usr/bin/env python3
"""
Test the new Databricks extraction function
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright
from main import extract_databricks_job

async def test_databricks_extraction():
    """Test the Databricks extraction function"""
    
    test_urls = [
        "https://www.databricks.com/company/careers/engineering---pipeline/staff-software-engineer---search-platform-7841778002?gh_jid=7841778002",
        "https://www.databricks.com/company/careers/finance/sr-accountant-8120171002?gh_jid=8120171002"
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for i, url in enumerate(test_urls, 1):
            try:
                page = await browser.new_page()
                print(f"\n🧪 Test {i}/{len(test_urls)}: {url}")
                
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Test the Databricks extraction
                job_data = {'url': url, 'company': 'Databricks'}
                result = await extract_databricks_job(page, job_data)
                
                print(f"\n📊 Results:")
                print(f"   Title: {result.get('title', 'Not found')}")
                print(f"   Company: {result.get('company', 'Not found')}")
                print(f"   Location: {result.get('location', 'Not found')}")
                print(f"   Employment Type: {result.get('employment_type', 'Not found')}")
                print(f"   Salary: {result.get('salary_range', 'Not found')}")
                print(f"   Description: {len(result.get('description', ''))} characters")
                print(f"   Job ID: {result.get('job_id', 'Not found')}")
                
                # Check for parsed sections
                sections = [k for k in result.keys() if k in ['requirements', 'responsibilities', 'benefits', 'experience_level', 'remote_type']]
                if sections:
                    print(f"   Parsed sections: {sections}")
                
                await page.close()
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_databricks_extraction())



