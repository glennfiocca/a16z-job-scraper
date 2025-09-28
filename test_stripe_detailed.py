#!/usr/bin/env python3
"""
Detailed test of Stripe job extraction to debug the extraction logic
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import extract_stripe_job

async def test_stripe_detailed():
    """Test Stripe job extraction with detailed debugging"""
    
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
            
            # Debug the JobsDetailCard specifically
            print(f"\n🔍 Debugging JobsDetailCard:")
            card_text = await page.evaluate('''
                () => {
                    const card = document.querySelector('.JobsDetailCard');
                    if (card) {
                        return card.innerText;
                    }
                    return null;
                }
            ''')
            
            if card_text:
                print(f"   JobsDetailCard text: '{card_text}'")
                
                # Test our extraction logic on this specific text
                lines = card_text.split('\n')
                print(f"   Lines in card:")
                for i, line in enumerate(lines):
                    print(f"     {i}: '{line.strip()}'")
                
                # Test location extraction
                for i, line in enumerate(lines):
                    if line.strip() == 'Office locations' and i + 1 < len(lines):
                        print(f"   ✅ Found location: '{lines[i + 1].strip()}'")
                        break
                
                # Test team extraction
                for i, line in enumerate(lines):
                    if line.strip() == 'Team' and i + 1 < len(lines):
                        print(f"   ✅ Found team: '{lines[i + 1].strip()}'")
                        break
                
                # Test job type extraction
                for i, line in enumerate(lines):
                    if line.strip() == 'Job type' and i + 1 < len(lines):
                        print(f"   ✅ Found job type: '{lines[i + 1].strip()}'")
                        break
            else:
                print("   ❌ JobsDetailCard not found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_stripe_detailed())
