#!/usr/bin/env python3
"""
Inspect Greenhouse job page structure to find location selectors
"""

import asyncio
from playwright.async_api import async_playwright

async def inspect_greenhouse_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to the Greenhouse job page
            url = "https://job-boards.greenhouse.io/waymark/jobs/4609499005"
            print(f"🔍 Inspecting: {url}")
            
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            print("\n📍 Looking for location elements...")
            
            # Try various location selectors
            location_selectors = [
                '.location',
                '[data-mapped="location"]',
                '.job-location',
                '.location-info',
                '.job-location-info',
                '[class*="location"]',
                '[data-location]',
                '.office-location',
                '.work-location'
            ]
            
            for selector in location_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"✅ Found {len(elements)} elements with selector: {selector}")
                        for i, element in enumerate(elements):
                            text = await element.inner_text()
                            print(f"   {i+1}. '{text.strip()}'")
                    else:
                        print(f"❌ No elements found with selector: {selector}")
                except Exception as e:
                    print(f"❌ Error with selector {selector}: {e}")
            
            # Look for any text containing "Remote" or location info
            print("\n🔍 Searching for location-related text...")
            try:
                location_text = await page.evaluate('''
                    () => {
                        const elements = document.querySelectorAll('*');
                        const locationCandidates = [];
                        
                        for (let el of elements) {
                            const text = el.innerText;
                            if (text && (
                                text.includes('Remote') || 
                                text.includes('US -') ||
                                text.includes('Job location:') ||
                                text.includes('Location:') ||
                                text.includes('San Francisco') ||
                                text.includes('New York') ||
                                text.includes('Los Angeles')
                            )) {
                                locationCandidates.push({
                                    tagName: el.tagName,
                                    className: el.className,
                                    text: text.trim().substring(0, 100)
                                });
                            }
                        }
                        return locationCandidates.slice(0, 10); // Return first 10 matches
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
            
            # Get page HTML structure around location
            print("\n🔍 Getting HTML structure...")
            try:
                html_content = await page.content()
                # Look for location-related HTML
                lines = html_content.split('\n')
                location_lines = []
                for i, line in enumerate(lines):
                    if any(keyword in line.lower() for keyword in ['remote', 'location', 'us -', 'job location']):
                        location_lines.append(f"Line {i}: {line.strip()}")
                        if len(location_lines) >= 10:  # Limit output
                            break
                
                if location_lines:
                    print("📍 HTML lines containing location info:")
                    for line in location_lines:
                        print(f"   {line}")
                else:
                    print("❌ No location-related HTML found")
                    
            except Exception as e:
                print(f"❌ Error getting HTML: {e}")
                
        except Exception as e:
            print(f"❌ Error loading page: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_greenhouse_page())



