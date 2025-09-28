#!/usr/bin/env python3
"""
Debug Databricks location extraction
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_databricks_location():
    """Debug location extraction on Databricks pages"""
    
    url = "https://www.databricks.com/company/careers/engineering---pipeline/staff-software-engineer---search-platform-7841778002?gh_jid=7841778002"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            print("🔍 Debugging location extraction...")
            
            # Get all paragraphs and their content
            paragraphs = await page.evaluate('''
                () => {
                    const paragraphs = document.querySelectorAll('p');
                    const results = [];
                    for (let i = 0; i < paragraphs.length; i++) {
                        const p = paragraphs[i];
                        const text = p.innerText.trim();
                        if (text && text.length > 0) {
                            results.push({
                                index: i,
                                text: text,
                                length: text.length
                            });
                        }
                    }
                    return results;
                }
            ''')
            
            print(f"Found {len(paragraphs)} paragraphs:")
            for i, p in enumerate(paragraphs[:10]):  # Show first 10
                print(f"   {i}: '{p['text'][:100]}...' (length: {p['length']})")
            
            # Look specifically for location patterns
            location_candidates = await page.evaluate('''
                () => {
                    const elements = document.querySelectorAll('*');
                    const candidates = [];
                    
                    for (let el of elements) {
                        const text = el.innerText;
                        if (text && (
                            text.includes('Bengaluru') || 
                            text.includes('India') || 
                            text.includes('Costa Rica') ||
                            text.includes('Remote') ||
                            text.includes('San Francisco') ||
                            text.includes('New York')
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
            
            print(f"\n📍 Location candidates:")
            for candidate in location_candidates[:5]:  # Show first 5
                print(f"   <{candidate['tagName']}> class='{candidate['className']}'")
                print(f"      Text: {candidate['text']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_databricks_location())
