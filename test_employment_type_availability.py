#!/usr/bin/env python3
"""
Test if employment type information is available on job pages
"""

import asyncio
from playwright.async_api import async_playwright

async def test_employment_type_availability():
    """Test if employment type info is available on different ATS platforms"""
    
    # Test URLs from different platforms
    test_cases = [
        {
            'platform': 'Greenhouse',
            'url': 'https://boards.greenhouse.io/spacex/jobs/8114054002',
            'expected_selectors': ['.employment-type', '[data-mapped="employment_type"]']
        },
        {
            'platform': 'Lever', 
            'url': 'https://jobs.lever.co/waymo/123456',
            'expected_selectors': ['.posting-categories .commitment', '.employment-type']
        },
        {
            'platform': 'Ashby',
            'url': 'https://jobs.ashbyhq.com/company/123456',
            'expected_selectors': ['div:has-text("Full time")', 'div:has-text("Employment Type")']
        },
        {
            'platform': 'Stripe',
            'url': 'https://stripe.com/jobs/listing/backend-engineer-billing/5932585',
            'expected_selectors': ['text="Job type"']
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
                
                # Test the expected selectors
                found_emp_type = False
                for selector in test_case['expected_selectors']:
                    try:
                        if selector.startswith('text='):
                            # Text-based search
                            text_to_find = selector.replace('text=', '').strip('"')
                            elements = await page.query_selector_all(f'text="{text_to_find}"')
                            if elements:
                                print(f"   ✅ Found text '{text_to_find}'")
                                found_emp_type = True
                        else:
                            # CSS selector
                            elements = await page.query_selector_all(selector)
                            if elements:
                                print(f"   ✅ Found {len(elements)} elements with selector: {selector}")
                                for i, element in enumerate(elements[:2]):
                                    text = await element.inner_text()
                                    print(f"      {i+1}. '{text.strip()}'")
                                found_emp_type = True
                    except Exception as e:
                        print(f"   ❌ Error with selector {selector}: {e}")
                
                if not found_emp_type:
                    print(f"   ❌ No employment type elements found with expected selectors")
                    
                    # Try to find any employment-related text
                    print(f"   🔍 Searching for employment-related text...")
                    emp_keywords = ['full time', 'part time', 'contract', 'employment', 'job type', 'commitment']
                    for keyword in emp_keywords:
                        try:
                            elements = await page.query_selector_all(f'text="{keyword}"')
                            if elements:
                                print(f"      Found '{keyword}': {len(elements)} elements")
                                for i, element in enumerate(elements[:2]):
                                    text = await element.inner_text()
                                    if len(text.strip()) < 100:  # Only show short text
                                        print(f"         {i+1}. '{text.strip()}'")
                        except:
                            pass
                
                await page.close()
                
            except Exception as e:
                print(f"   💥 ERROR: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_employment_type_availability())

