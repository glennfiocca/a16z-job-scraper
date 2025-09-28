#!/usr/bin/env python3
"""
Test Databricks job extraction to understand the page structure
"""

import asyncio
from playwright.async_api import async_playwright

async def test_databricks_extraction():
    """Test extraction on Databricks job pages"""
    
    # Sample Databricks URLs
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
                location_selectors = [
                    'h1 + p',  # Paragraph after h1
                    '.location', 
                    '[class*="location"]',
                    'p:contains("India")',
                    'p:contains("Costa Rica")',
                    'p:contains("Bengaluru")'
                ]
                
                location = None
                for selector in location_selectors:
                    try:
                        if ':contains(' in selector:
                            # Use evaluate for text-based selectors
                            location = await page.evaluate(f'''
                                () => {{
                                    const elements = document.querySelectorAll('p');
                                    for (let el of elements) {{
                                        if (el.innerText.includes('India') || el.innerText.includes('Costa Rica') || el.innerText.includes('Bengaluru')) {{
                                            return el.innerText.trim();
                                        }}
                                    }}
                                    return null;
                                }}
                            ''')
                        else:
                            element = await page.query_selector(selector)
                            if element:
                                location = await element.inner_text()
                        
                        if location and location.strip():
                            print(f"   📍 Location ({selector}): {location.strip()}")
                            break
                    except:
                        continue
                
                # Test description extraction
                desc_selectors = ['main', '.job-description', '.content', 'article']
                description = None
                for selector in desc_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            description = await element.inner_text()
                            if description and len(description.strip()) > 500:
                                print(f"   📄 Description ({selector}): {len(description)} characters")
                                break
                    except:
                        continue
                
                # Test salary extraction (expecting none)
                salary_selectors = ['.salary', '.compensation', '.pay-range', '[class*="salary"]']
                salary = None
                for selector in salary_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            salary = await element.inner_text()
                            if salary and salary.strip():
                                print(f"   💰 Salary ({selector}): {salary.strip()}")
                                break
                    except:
                        continue
                
                if not salary:
                    print(f"   💰 Salary: Not found (as expected)")
                
                # Test for any salary-related text in content
                salary_in_content = await page.evaluate('''
                    () => {
                        const text = document.body.innerText;
                        const salaryKeywords = ['$', 'salary', 'compensation', 'pay', 'wage', 'k/year', 'per year'];
                        for (let keyword of salaryKeywords) {
                            if (text.toLowerCase().includes(keyword.toLowerCase())) {
                                return text.substring(text.toLowerCase().indexOf(keyword.toLowerCase()) - 50, text.toLowerCase().indexOf(keyword.toLowerCase()) + 100);
                            }
                        }
                        return null;
                    }
                ''')
                
                if salary_in_content:
                    print(f"   💰 Salary in content: {salary_in_content}")
                else:
                    print(f"   💰 No salary keywords found in content")
                
                await page.close()
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_databricks_extraction())
