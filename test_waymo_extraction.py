#!/usr/bin/env python3
"""
Test Waymo job extraction to understand the page structure
"""

import asyncio
from playwright.async_api import async_playwright

async def test_waymo_extraction():
    """Test extraction on Waymo job pages"""
    
    url = "https://careers.withwaymo.com/jobs/senior-manager-federal-policy-and-government-affairs-washington-district-of-columbia-united-states?gh_jid=6641637"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print(f"🧪 Testing Waymo extraction: {url}")
            
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Test title extraction
            title_selectors = ['h1', '.job-title', 'title']
            title = None
            for selector in title_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        title = await element.inner_text()
                        if title and title.strip():
                            print(f"   📝 Title ({selector}): {title.strip()}")
                            break
                except:
                    continue
            
            # Test location extraction
            print(f"\n📍 Testing location extraction...")
            location_candidates = await page.evaluate('''
                () => {
                    const elements = document.querySelectorAll('*');
                    const candidates = [];
                    
                    for (let el of elements) {
                        const text = el.innerText;
                        if (text && (
                            text.includes('Washington') || 
                            text.includes('District of Columbia') ||
                            text.includes('United States') ||
                            text.includes('California') ||
                            text.includes('Mountain View') ||
                            text.includes('San Francisco') ||
                            text.includes('Remote')
                        )) {
                            candidates.push({
                                tagName: el.tagName,
                                className: el.className,
                                text: text.trim().substring(0, 200)
                            });
                        }
                    }
                    return candidates;
                }
            ''')
            
            print(f"   Location candidates:")
            for candidate in location_candidates[:5]:
                print(f"      <{candidate['tagName']}> class='{candidate['className']}'")
                print(f"         Text: {candidate['text']}")
            
            # Test salary extraction
            print(f"\n💰 Testing salary extraction...")
            salary_candidates = await page.evaluate('''
                () => {
                    const elements = document.querySelectorAll('*');
                    const candidates = [];
                    
                    for (let el of elements) {
                        const text = el.innerText;
                        if (text && (
                            text.includes('$') || 
                            text.includes('salary') || 
                            text.includes('compensation') ||
                            text.includes('USD') ||
                            text.includes('204,000') ||
                            text.includes('259,000')
                        )) {
                            candidates.push({
                                tagName: el.tagName,
                                className: el.className,
                                text: text.trim().substring(0, 200)
                            });
                        }
                    }
                    return candidates;
                }
            ''')
            
            print(f"   Salary candidates:")
            for candidate in salary_candidates[:5]:
                print(f"      <{candidate['tagName']}> class='{candidate['className']}'")
                print(f"         Text: {candidate['text']}")
            
            # Test description extraction
            print(f"\n📄 Testing description extraction...")
            desc_selectors = ['main', '.job-description', '.content', 'article']
            description = None
            for selector in desc_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        description = await element.inner_text()
                        if description and len(description.strip()) > 500:
                            print(f"   Description ({selector}): {len(description)} characters")
                            break
                except:
                    continue
            
            await page.close()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_waymo_extraction())


