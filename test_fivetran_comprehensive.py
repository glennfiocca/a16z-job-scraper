#!/usr/bin/env python3
"""
Test the comprehensive Fivetran extraction function
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright
from main import extract_fivetran_job

async def test_fivetran_comprehensive():
    """Test the comprehensive Fivetran extraction function"""
    
    url = "https://www.fivetran.com/careers/job?gh_jid=6346785003"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print(f"🧪 Testing comprehensive Fivetran extraction: {url}")
            
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('domcontentloaded', timeout=15000)
            
            # Test the Fivetran extraction
            job_data = {'url': url, 'company': 'Fivetran'}
            result = await extract_fivetran_job(page, job_data)
            
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
                for section in sections:
                    content = result.get(section, '')
                    if content:
                        print(f"      {section}: {len(content)} characters")
            
            await page.close()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_fivetran_comprehensive())
