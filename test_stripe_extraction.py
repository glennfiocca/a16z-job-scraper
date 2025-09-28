#!/usr/bin/env python3
"""
Test Stripe job extraction to see what data is being captured
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import extract_stripe_job

async def test_stripe_extraction():
    """Test Stripe job extraction on the example URL"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Test the specific Stripe URL
            url = "https://stripe.com/jobs/listing/backend-engineer-billing/5932585"
            print(f"🧪 Testing Stripe extraction for: {url}")
            
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Test the current extraction
            job_data = {'url': url, 'company': 'Stripe'}
            result = await extract_stripe_job(page, job_data)
            
            print(f"\n📊 Current Extraction Results:")
            print(f"   Title: {result.get('title', 'NOT FOUND')}")
            print(f"   Company: {result.get('company', 'NOT FOUND')}")
            print(f"   Location: {result.get('location', 'NOT FOUND')}")
            print(f"   Employment Type: {result.get('employment_type', 'NOT FOUND')}")
            print(f"   Description: {result.get('description', 'NOT FOUND')[:100]}..." if result.get('description') else "NOT FOUND")
            
            # Now let's inspect the actual page structure
            print(f"\n🔍 Page Structure Analysis:")
            
            # Check for title elements
            title_elements = await page.query_selector_all('h1, h2, .job-title, .title')
            print(f"   Found {len(title_elements)} potential title elements:")
            for i, el in enumerate(title_elements[:5]):
                text = await el.inner_text()
                print(f"     {i+1}. '{text.strip()}'")
            
            # Check for location elements
            location_elements = await page.query_selector_all('.location, .office-location, [class*="location"]')
            print(f"   Found {len(location_elements)} potential location elements")
            
            # Look for any text containing location info
            location_text = await page.evaluate('''
                () => {
                    const elements = document.querySelectorAll('*');
                    const locationCandidates = [];
                    
                    for (let el of elements) {
                        const text = el.innerText;
                        if (text && (
                            text.includes('Toronto') || 
                            text.includes('Office locations') ||
                            text.includes('Location') ||
                            text.includes('Remote') ||
                            text.includes('San Francisco') ||
                            text.includes('New York')
                        )) {
                            locationCandidates.push({
                                tagName: el.tagName,
                                className: el.className,
                                text: text.trim().substring(0, 100)
                            });
                        }
                    }
                    return locationCandidates.slice(0, 10);
                }
            ''')
            
            if location_text:
                print(f"   Location-related text found:")
                for i, item in enumerate(location_text):
                    print(f"     {i+1}. <{item['tagName']}> class='{item['className']}' text='{item['text']}'")
            
            # Check for employment type
            emp_type_text = await page.evaluate('''
                () => {
                    const elements = document.querySelectorAll('*');
                    for (let el of elements) {
                        const text = el.innerText;
                        if (text && (text.includes('Full time') || text.includes('Job type'))) {
                            return text.trim().substring(0, 200);
                        }
                    }
                    return null;
                }
            ''')
            
            if emp_type_text:
                print(f"   Employment type text: '{emp_type_text}'")
            
                
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_stripe_extraction())
