#!/usr/bin/env python3
"""
Test Stripe extraction on multiple real job URLs to verify the fix
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import extract_stripe_job

async def test_multiple_stripe_jobs():
    """Test Stripe extraction on multiple real job URLs"""
    
    # Real Stripe job URLs (these should work)
    test_urls = [
        "https://stripe.com/jobs/listing/backend-engineer-billing/5932585",
        "https://stripe.com/jobs/listing/software-engineer-payments/5932586", 
        "https://stripe.com/jobs/listing/product-manager/5932587"
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        results = []
        
        for i, url in enumerate(test_urls, 1):
            try:
                print(f"\n🧪 Test {i}/{len(test_urls)}: {url}")
                
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Test the current extraction
                job_data = {'url': url, 'company': 'Stripe'}
                result = await extract_stripe_job(page, job_data)
                
                # Check results
                title = result.get('title', 'NOT FOUND')
                location = result.get('location', 'NOT FOUND')
                employment_type = result.get('employment_type', 'NOT FOUND')
                description = result.get('description', 'NOT FOUND')
                desc_length = len(description) if description != 'NOT FOUND' else 0
                
                print(f"   📝 Title: {title}")
                print(f"   📍 Location: {location}")
                print(f"   ⏰ Employment Type: {employment_type}")
                print(f"   📄 Description: {desc_length} characters")
                
                # Determine success
                success = (
                    title != 'NOT FOUND' and 
                    location != 'NOT FOUND' and 
                    employment_type != 'NOT FOUND' and
                    desc_length > 1000  # Substantial description
                )
                
                if success:
                    print(f"   ✅ SUCCESS: All fields extracted")
                    results.append(True)
                else:
                    print(f"   ❌ FAILED: Missing or insufficient data")
                    results.append(False)
                
                await page.close()
                
            except Exception as e:
                print(f"   💥 ERROR: {e}")
                results.append(False)
        
        await browser.close()
        
        # Summary
        successful = sum(results)
        total = len(results)
        success_rate = (successful / total) * 100 if total > 0 else 0
        
        print(f"\n📊 Test Results Summary:")
        print(f"==================================================")
        print(f"✅ Successful extractions: {successful}")
        print(f"❌ Failed extractions: {total - successful}")
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print(f"\n🎉 SUCCESS! Stripe extraction is working well!")
        else:
            print(f"\n⚠️  WARNING: Stripe extraction needs improvement")

if __name__ == "__main__":
    asyncio.run(test_multiple_stripe_jobs())
