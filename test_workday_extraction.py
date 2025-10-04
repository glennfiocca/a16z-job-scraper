#!/usr/bin/env python3
"""
Test Workday job extraction to understand the page structure
"""

import asyncio
from playwright.async_api import async_playwright

async def test_workday_extraction():
    """Test Workday job extraction on a real job URL"""
    
    # Test URL from the database
    test_url = "https://rappi.wd12.myworkdayjobs.com/Rappi_jobs/job/COL-Bogot/Marketing-CRM-Automations-Analyst_JR117283"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Use headless=False to see the page
        page = await browser.new_page()
        
        try:
            print(f"🧪 Testing Workday extraction: {test_url}")
            
            await page.goto(test_url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Get page title
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Look for common job elements
            print(f"\n🔍 Looking for job elements...")
            
            # Title selectors
            title_selectors = [
                'h1[data-automation-id="jobPostingHeader"]',
                'h1',
                '.job-title',
                '[data-automation-id="jobTitle"]'
            ]
            
            for selector in title_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"✅ Found {len(elements)} elements with title selector: {selector}")
                        for i, element in enumerate(elements[:2]):
                            text = await element.inner_text()
                            print(f"   {i+1}. '{text.strip()}'")
                    else:
                        print(f"❌ No elements found with title selector: {selector}")
                except Exception as e:
                    print(f"❌ Error with title selector {selector}: {e}")
            
            # Location selectors
            print(f"\n📍 Looking for location elements...")
            location_selectors = [
                '[data-automation-id="jobPostingLocation"]',
                '.location',
                '[data-automation-id="location"]',
                '[class*="location"]'
            ]
            
            for selector in location_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"✅ Found {len(elements)} elements with location selector: {selector}")
                        for i, element in enumerate(elements[:2]):
                            text = await element.inner_text()
                            print(f"   {i+1}. '{text.strip()}'")
                    else:
                        print(f"❌ No elements found with location selector: {selector}")
                except Exception as e:
                    print(f"❌ Error with location selector {selector}: {e}")
            
            # Employment type selectors
            print(f"\n⏰ Looking for employment type elements...")
            emp_type_selectors = [
                '[data-automation-id="jobPostingEmploymentType"]',
                '.employment-type',
                '[data-automation-id="employmentType"]',
                '[class*="employment"]'
            ]
            
            for selector in emp_type_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"✅ Found {len(elements)} elements with employment type selector: {selector}")
                        for i, element in enumerate(elements[:2]):
                            text = await element.inner_text()
                            print(f"   {i+1}. '{text.strip()}'")
                    else:
                        print(f"❌ No elements found with employment type selector: {selector}")
                except Exception as e:
                    print(f"❌ Error with employment type selector {selector}: {e}")
            
            # Description selectors
            print(f"\n📝 Looking for description elements...")
            desc_selectors = [
                '[data-automation-id="jobPostingDescription"]',
                '.job-description',
                '[data-automation-id="description"]',
                'main',
                '.content'
            ]
            
            for selector in desc_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"✅ Found {len(elements)} elements with description selector: {selector}")
                        for i, element in enumerate(elements[:1]):
                            text = await element.inner_text()
                            if text and len(text.strip()) > 100:
                                print(f"   {i+1}. Length: {len(text)} chars, Preview: '{text.strip()[:100]}...'")
                            else:
                                print(f"   {i+1}. '{text.strip()}'")
                    else:
                        print(f"❌ No elements found with description selector: {selector}")
                except Exception as e:
                    print(f"❌ Error with description selector {selector}: {e}")
            
            # Look for any text containing location info
            print(f"\n🔍 Searching for location-related text...")
            try:
                location_text = await page.evaluate('''
                    () => {
                        const elements = document.querySelectorAll('*');
                        const locationCandidates = [];
                        
                        for (let el of elements) {
                            const text = el.innerText;
                            if (text && (
                                text.includes('Bogot') || 
                                text.includes('Colombia') ||
                                text.includes('Location') ||
                                text.includes('Remote') ||
                                text.includes('Hybrid') ||
                                text.includes('On-site')
                            )) {
                                locationCandidates.push({
                                    tagName: el.tagName,
                                    className: el.className,
                                    text: text.trim().substring(0, 100)
                                });
                            }
                        }
                        return locationCandidates.slice(0, 5); // Return first 5 matches
                    }
                ''')
                
                if location_text:
                    print("📍 Location-related text found:")
                    for i, item in enumerate(location_text):
                        print(f"   {i+1}. <{item['tagName']}> class='{item['className']}' text='{item['text']}'")
                else:
                    print("❌ No location-related text found")
                    
            except Exception as e:
                print(f"❌ Error searching for location text: {e}")
            
        except Exception as e:
            print(f"❌ Error during inspection: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_workday_extraction())





