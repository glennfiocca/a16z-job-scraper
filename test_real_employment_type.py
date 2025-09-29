#!/usr/bin/env python3
"""
Test employment type availability on real job pages
"""

import asyncio
from playwright.async_api import async_playwright

async def test_real_employment_type():
    """Test employment type on real job pages"""
    
    # Real job URLs that should work
    test_cases = [
        {
            'platform': 'Greenhouse',
            'url': 'https://boards.greenhouse.io/spacex/jobs/8114054002',
            'company': 'SpaceX'
        },
        {
            'platform': 'Lever', 
            'url': 'https://jobs.lever.co/waymo/123456',  # This might not exist
            'company': 'Waymo'
        },
        {
            'platform': 'Ashby',
            'url': 'https://jobs.ashbyhq.com/company/123456',  # This might not exist
            'company': 'Unknown'
        },
        {
            'platform': 'Stripe',
            'url': 'https://stripe.com/jobs/listing/backend-engineer-billing/5932585',
            'company': 'Stripe'
        }
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for test_case in test_cases:
            try:
                print(f"\n🧪 Testing {test_case['platform']}: {test_case['url']}")
                
                page = await browser.new_page()
                await page.goto(test_case['url'], timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Check if page loaded successfully
                title = await page.title()
                print(f"   📄 Page title: {title}")
                
                # Look for employment type in the page content
                print(f"   🔍 Searching for employment type information...")
                
                # Search for common employment type keywords
                emp_keywords = ['full time', 'part time', 'contract', 'employment', 'job type', 'commitment', 'permanent', 'temporary']
                found_keywords = []
                
                for keyword in emp_keywords:
                    try:
                        # Search for text containing the keyword
                        elements = await page.query_selector_all(f'text="{keyword}"')
                        if elements:
                            found_keywords.append(keyword)
                            print(f"      ✅ Found '{keyword}': {len(elements)} elements")
                            
                            # Show context for first few matches
                            for i, element in enumerate(elements[:2]):
                                try:
                                    text = await element.inner_text()
                                    if len(text.strip()) < 200:  # Only show reasonable length text
                                        print(f"         {i+1}. '{text.strip()}'")
                                except:
                                    pass
                    except Exception as e:
                        pass
                
                if not found_keywords:
                    print(f"   ❌ No employment type keywords found")
                    
                    # Try to find any structured data or metadata
                    print(f"   🔍 Checking for structured data...")
                    try:
                        # Look for meta tags or structured data
                        meta_employment = await page.query_selector('meta[name*="employment"], meta[property*="employment"]')
                        if meta_employment:
                            content = await meta_employment.get_attribute('content')
                            print(f"      Found meta employment: {content}")
                        else:
                            print(f"      No employment meta tags found")
                    except:
                        pass
                
                await page.close()
                
            except Exception as e:
                print(f"   💥 ERROR: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_real_employment_type())

