#!/usr/bin/env python3
"""
Test script to compare AI parsing vs current parsing for Greenhouse jobs
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Job
from ai_parser import ai_parser
from main import parse_greenhouse_sections, extract_greenhouse_job
from playwright.async_api import async_playwright
import json
from datetime import datetime

async def test_ai_parsing(limit=10):
    """Test AI parsing on a small batch of Greenhouse jobs"""
    
    app = create_app()
    
    with app.app_context():
        print("🤖 AI PARSER TEST")
        print("=" * 50)
        
        # Get recent Greenhouse jobs
        greenhouse_jobs = Job.query.filter(
            Job.source_url.like('%greenhouse%')
        ).order_by(Job.scraped_at.desc()).limit(limit).all()
        
        print(f"📊 Testing on {len(greenhouse_jobs)} Greenhouse jobs")
        print()
        
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            for i, job in enumerate(greenhouse_jobs, 1):
                print(f"🔍 Testing job {i}/{len(greenhouse_jobs)}: {job.title}")
                
                try:
                    # Get the page content
                    page = await browser.new_page()
                    await page.goto(job.source_url, timeout=10000)
                    await page.wait_for_timeout(2000)  # Wait for content to load
                    
                    # Get raw content
                    raw_content = await page.inner_text('body')
                    
                    # Test AI parsing
                    print("   🤖 AI parsing...")
                    ai_result = await ai_parser.parse_greenhouse_job(raw_content, job.source_url)
                    
                    # Test current parsing (simulate)
                    print("   📝 Current parsing...")
                    current_result = await parse_greenhouse_sections(raw_content)
                    
                    # Compare results
                    comparison = {
                        'job_id': job.id,
                        'url': job.source_url,
                        'title': job.title,
                        'ai_result': ai_result,
                        'current_result': current_result,
                        'improvements': []
                    }
                    
                    # Check for improvements
                    if ai_result.get('title') and not current_result.get('title'):
                        comparison['improvements'].append("✅ AI extracted title")
                    if ai_result.get('location') and not current_result.get('location'):
                        comparison['improvements'].append("✅ AI extracted location")
                    if ai_result.get('requirements') and not current_result.get('requirements'):
                        comparison['improvements'].append("✅ AI extracted requirements")
                    if ai_result.get('benefits') and not current_result.get('benefits'):
                        comparison['improvements'].append("✅ AI extracted benefits")
                    
                    results.append(comparison)
                    
                    # Show improvements for this job
                    if comparison['improvements']:
                        print(f"   🎉 Improvements: {', '.join(comparison['improvements'])}")
                    else:
                        print("   ⚠️  No clear improvements detected")
                    
                    await page.close()
                    
                except Exception as e:
                    print(f"   ❌ Error testing job {job.id}: {e}")
                    continue
            
            await browser.close()
        
        # Summary
        print("\n📈 SUMMARY")
        print("=" * 30)
        
        total_improvements = sum(len(r['improvements']) for r in results)
        jobs_with_improvements = len([r for r in results if r['improvements']])
        
        print(f"Total improvements: {total_improvements}")
        print(f"Jobs with improvements: {jobs_with_improvements}/{len(results)}")
        print(f"Success rate: {jobs_with_improvements/len(results)*100:.1f}%")
        
        # Show detailed results
        print("\n🔍 DETAILED RESULTS")
        for r in results[:5]:  # Show first 5
            print(f"\nJob: {r['title']}")
            print(f"URL: {r['url']}")
            if r['improvements']:
                print(f"Improvements: {', '.join(r['improvements'])}")
            else:
                print("No improvements")
        
        return results

async def main():
    """Main test function"""
    print("Starting AI parser test...")
    
    # Test with 10 jobs first
    results = await test_ai_parsing(limit=10)
    
    print(f"\n✅ Test completed! Check results above.")
    print(f"💡 If results look good, we can integrate this into your main scraping pipeline.")

if __name__ == "__main__":
    asyncio.run(main())




