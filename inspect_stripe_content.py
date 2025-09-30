#!/usr/bin/env python3
"""
Inspect Stripe job page structure to find content selectors
"""

import asyncio
from playwright.async_api import async_playwright

async def inspect_stripe_content():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to the Stripe job page
            url = "https://stripe.com/jobs/listing/backend-engineer-billing/5932585"
            print(f"🔍 Inspecting Stripe content structure: {url}")
            
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            print("\n📝 Looking for content elements...")
            
            # Try various content selectors
            content_selectors = [
                'main',
                '.job-description',
                '.content',
                'article',
                '[role="main"]',
                '.job-content',
                '.description',
                '.job-details',
                '.posting-content',
                '.job-posting',
                'section',
                '.section',
                '[class*="content"]',
                '[class*="description"]',
                '[class*="job"]'
            ]
            
            for selector in content_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"✅ Found {len(elements)} elements with selector: {selector}")
                        for i, element in enumerate(elements[:3]):  # Show first 3
                            text = await element.inner_text()
                            if text and len(text.strip()) > 50:
                                print(f"   {i+1}. Length: {len(text)} chars, Preview: '{text.strip()[:100]}...'")
                    else:
                        print(f"❌ No elements found with selector: {selector}")
                except Exception as e:
                    print(f"❌ Error with selector {selector}: {e}")
            
            # Look for any text containing job description content
            print("\n🔍 Searching for job description content...")
            try:
                # Get all text content and look for substantial content
                all_text = await page.evaluate('''
                    () => {
                        const elements = document.querySelectorAll('*');
                        const contentCandidates = [];
                        
                        for (let el of elements) {
                            const text = el.innerText;
                            if (text && text.length > 500) {  // Look for substantial content
                                // Check if it contains job-related keywords
                                if (text.includes('responsibilities') || 
                                    text.includes('requirements') || 
                                    text.includes('qualifications') ||
                                    text.includes('experience') ||
                                    text.includes('skills') ||
                                    text.includes('benefits') ||
                                    text.includes('About') ||
                                    text.includes('What you') ||
                                    text.includes('You will')) {
                                    contentCandidates.push({
                                        tagName: el.tagName,
                                        className: el.className,
                                        id: el.id,
                                        textLength: text.length,
                                        preview: text.substring(0, 200)
                                    });
                                }
                            }
                        }
                        return contentCandidates.slice(0, 10); // Return first 10 matches
                    }
                ''')
                
                if content_text:
                    print("📝 Job description content found:")
                    for i, item in enumerate(content_text):
                        print(f"   {i+1}. <{item['tagName']}> class='{item['className']}' id='{item['id']}' length={item['textLength']}")
                        print(f"      Preview: '{item['preview']}...'")
                else:
                    print("❌ No substantial job description content found")
                    
            except Exception as e:
                print(f"❌ Error searching for content: {e}")
            
            # Get page HTML structure around main content
            print("\n🔍 Getting HTML structure...")
            try:
                html_content = await page.content()
                # Look for main content sections
                if 'main' in html_content:
                    print("✅ Found 'main' tag in HTML")
                if 'article' in html_content:
                    print("✅ Found 'article' tag in HTML")
                if 'section' in html_content:
                    print("✅ Found 'section' tag in HTML")
                
                # Look for common content patterns
                content_patterns = [
                    'job-description',
                    'job-content', 
                    'posting-content',
                    'description',
                    'content'
                ]
                
                for pattern in content_patterns:
                    if pattern in html_content:
                        print(f"✅ Found '{pattern}' in HTML")
                    else:
                        print(f"❌ '{pattern}' not found in HTML")
                        
            except Exception as e:
                print(f"❌ Error getting HTML structure: {e}")
            
            # Try to find the actual job description by looking for specific text patterns
            print("\n🔍 Looking for specific job description patterns...")
            try:
                job_desc_text = await page.evaluate('''
                    () => {
                        // Look for text that contains job description patterns
                        const allElements = document.querySelectorAll('*');
                        for (let el of allElements) {
                            const text = el.innerText;
                            if (text && text.length > 1000) {  // Substantial content
                                // Check if it looks like a job description
                                const hasJobKeywords = text.includes('responsibilities') || 
                                                     text.includes('requirements') || 
                                                     text.includes('qualifications') ||
                                                     text.includes('About') ||
                                                     text.includes('What you') ||
                                                     text.includes('You will') ||
                                                     text.includes('experience') ||
                                                     text.includes('skills');
                                
                                if (hasJobKeywords) {
                                    return {
                                        tagName: el.tagName,
                                        className: el.className,
                                        id: el.id,
                                        textLength: text.length,
                                        preview: text.substring(0, 300)
                                    };
                                }
                            }
                        }
                        return null;
                    }
                ''')
                
                if job_desc_text:
                    print("🎯 Found job description content:")
                    print(f"   Tag: <{job_desc_text['tagName']}>")
                    print(f"   Class: {job_desc_text['className']}")
                    print(f"   ID: {job_desc_text['id']}")
                    print(f"   Length: {job_desc_text['textLength']} characters")
                    print(f"   Preview: '{job_desc_text['preview']}...'")
                else:
                    print("❌ No job description content found")
                    
            except Exception as e:
                print(f"❌ Error finding job description: {e}")
                
        except Exception as e:
            print(f"❌ Error during inspection: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_stripe_content())




