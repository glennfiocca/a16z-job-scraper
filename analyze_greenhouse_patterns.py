#!/usr/bin/env python3
"""
Comprehensive analysis of Greenhouse job patterns across 30 companies
"""

import asyncio
import json
from playwright.async_api import async_playwright
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import extract_greenhouse_job

# 30 Greenhouse job URLs for analysis
GREENHOUSE_URLS = [
    "https://job-boards.greenhouse.io/waymark/jobs/4595277005",
    "https://job-boards.greenhouse.io/andurilindustries/jobs/4925653007?gh_jid=4925653007",
    "https://job-boards.greenhouse.io/flexport/jobs/7202407?gh_jid=7202407",
    "https://job-boards.greenhouse.io/figma/jobs/5641078004?gh_jid=5641078004",
    "https://job-boards.greenhouse.io/appliedintuition/jobs/4376428005?gh_jid=4376428005",
    "https://job-boards.greenhouse.io/labelbox/jobs/4927163007",
    "https://job-boards.greenhouse.io/astranis/jobs/4606980006",
    "https://job-boards.greenhouse.io/headway/jobs/5669636004",
    "https://job-boards.greenhouse.io/carta/jobs/7487461003",
    "https://job-boards.greenhouse.io/pomelocare/jobs/5662273004",
    "https://job-boards.greenhouse.io/cresta/jobs/4941475008",
    "https://job-boards.greenhouse.io/radiant/jobs/4615402005",
    "https://job-boards.greenhouse.io/earnin/jobs/7296612",
    "https://job-boards.greenhouse.io/mercury/jobs/5669672004",
    "https://job-boards.greenhouse.io/dbtlabsinc/jobs/4614042005",
    "https://job-boards.greenhouse.io/mixpanel/jobs/7289439",
    "https://job-boards.greenhouse.io/dialpad/jobs/8192985002",
    "https://job-boards.greenhouse.io/benchling/jobs/7298483?gh_jid=7298483",
    "https://job-boards.greenhouse.io/starburst/jobs/4939493008",
    "https://job-boards.greenhouse.io/hebbia/jobs/4614766005",
    "https://job-boards.greenhouse.io/udacity/jobs/8183464002",
    "https://job-boards.greenhouse.io/omadahealth/jobs/7279592",
    "https://job-boards.greenhouse.io/arcboatcompany/jobs/4930338008",
    "https://job-boards.greenhouse.io/spotoncorporate/jobs/7452218003",
    "https://job-boards.greenhouse.io/everlaw/jobs/4605005006",
    "https://job-boards.greenhouse.io/komodohealth/jobs/8194191002",
    "https://job-boards.greenhouse.io/alchemy/jobs/4614176005",
    "https://job-boards.greenhouse.io/koboldmetals/jobs/4614074005",
    "https://job-boards.greenhouse.io/paveakatroveinformationtechnologies/jobs/4614678005",
    "https://job-boards.greenhouse.io/thatch/jobs/4938224008"
]

async def analyze_greenhouse_patterns():
    """Analyze patterns across 30 Greenhouse job postings"""
    
    results = []
    failed_urls = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for i, url in enumerate(GREENHOUSE_URLS, 1):
            try:
                print(f"\n🔍 Analyzing job {i}/30: {url}")
                
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Extract company name from URL
                company_name = url.split('/')[-3] if 'greenhouse.io' in url else 'Unknown'
                
                # Extract job data
                job_data = {'url': url, 'company': company_name}
                result = await extract_greenhouse_job(page, job_data)
                
                if result:
                    # Add analysis metadata
                    result['analysis_metadata'] = {
                        'job_number': i,
                        'company_from_url': company_name,
                        'scraping_success': True,
                        'fields_populated': count_populated_fields(result)
                    }
                    
                    results.append(result)
                    print(f"   ✅ Success: {result.get('title', 'Unknown Title')} at {company_name}")
                else:
                    print(f"   ❌ Filtered out")
                    failed_urls.append({'url': url, 'error': 'Job filtered out (contract/part-time)'})
                
                await page.close()
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                failed_urls.append({'url': url, 'error': str(e)})
                continue
        
        await browser.close()
    
    # Save results for analysis
    with open('/home/runner/workspace/greenhouse_analysis_results.json', 'w') as f:
        json.dump({
            'successful_jobs': results,
            'failed_jobs': failed_urls,
            'total_analyzed': len(results),
            'total_failed': len(failed_urls)
        }, f, indent=2)
    
    # Analyze patterns
    analyze_field_patterns(results)
    
    return results, failed_urls

def count_populated_fields(job_data):
    """Count how many fields are populated"""
    fields = ['title', 'company', 'location', 'employment_type', 'description', 
              'responsibilities', 'requirements', 'benefits', 'work_environment',
              'salary_range', 'salary_min', 'salary_max']
    
    populated = 0
    for field in fields:
        if job_data.get(field) and job_data[field] not in ['Not found', 'Not provided', 'Not specified', None]:
            populated += 1
    
    return populated

def analyze_field_patterns(results):
    """Analyze patterns across all scraped jobs"""
    
    print(f"\n📊 PATTERN ANALYSIS RESULTS")
    print("=" * 60)
    
    # Field completion rates
    fields = ['title', 'company', 'location', 'employment_type', 'description', 
              'responsibilities', 'requirements', 'benefits', 'work_environment',
              'salary_range', 'salary_min', 'salary_max']
    
    print(f"\n📈 FIELD COMPLETION RATES:")
    print("-" * 40)
    
    for field in fields:
        populated_count = sum(1 for job in results if job.get(field) and 
                             job[field] not in ['Not found', 'Not provided', 'Not specified', None])
        completion_rate = (populated_count / len(results)) * 100
        print(f"   {field:20}: {populated_count:2}/{len(results):2} ({completion_rate:5.1f}%)")
    
    # Employment type analysis
    print(f"\n💼 EMPLOYMENT TYPE ANALYSIS:")
    print("-" * 40)
    emp_types = {}
    for job in results:
        emp_type = job.get('employment_type', 'Unknown')
        emp_types[emp_type] = emp_types.get(emp_type, 0) + 1
    
    for emp_type, count in emp_types.items():
        print(f"   {emp_type:20}: {count:2} jobs")
    
    # Work environment analysis
    print(f"\n🏢 WORK ENVIRONMENT ANALYSIS:")
    print("-" * 40)
    work_envs = {}
    for job in results:
        work_env = job.get('work_environment', 'Unknown')
        work_envs[work_env] = work_envs.get(work_env, 0) + 1
    
    for work_env, count in work_envs.items():
        print(f"   {work_env:20}: {count:2} jobs")
    
    # Salary analysis
    print(f"\n💰 SALARY ANALYSIS:")
    print("-" * 40)
    salary_ranges = [job.get('salary_range') for job in results if job.get('salary_range') and 
                     job['salary_range'] not in ['Not provided', 'Not specified']]
    print(f"   Jobs with salary info: {len(salary_ranges)}/{len(results)}")
    
    if salary_ranges:
        print(f"   Sample salary ranges:")
        for i, salary in enumerate(salary_ranges[:5]):
            print(f"     {i+1}. {salary}")
    
    # Location analysis
    print(f"\n📍 LOCATION ANALYSIS:")
    print("-" * 40)
    locations = [job.get('location') for job in results if job.get('location')]
    print(f"   Jobs with location: {len(locations)}/{len(results)}")
    
    if locations:
        print(f"   Sample locations:")
        for i, location in enumerate(locations[:10]):
            print(f"     {i+1}. {location}")
    
    # Section parsing analysis
    print(f"\n📝 SECTION PARSING ANALYSIS:")
    print("-" * 40)
    
    sections = ['responsibilities', 'requirements', 'benefits']
    for section in sections:
        section_data = [job.get(section) for job in results if job.get(section) and 
                       job[section] not in ['Not found', 'Not provided', 'Not specified']]
        avg_length = sum(len(str(data)) for data in section_data) / len(section_data) if section_data else 0
        print(f"   {section:15}: {len(section_data):2} jobs, avg {avg_length:.0f} chars")
    
    # Company-specific patterns
    print(f"\n🏢 COMPANY-SPECIFIC PATTERNS:")
    print("-" * 40)
    
    company_stats = {}
    for job in results:
        company = job.get('company', 'Unknown')
        if company not in company_stats:
            company_stats[company] = {
                'total_jobs': 0,
                'fields_populated': 0,
                'has_salary': False,
                'has_benefits': False
            }
        
        company_stats[company]['total_jobs'] += 1
        company_stats[company]['fields_populated'] += job.get('analysis_metadata', {}).get('fields_populated', 0)
        
        if job.get('salary_range') and job['salary_range'] not in ['Not provided', 'Not specified']:
            company_stats[company]['has_salary'] = True
        
        if job.get('benefits') and job['benefits'] not in ['Not found', 'Not provided', 'Not specified']:
            company_stats[company]['has_benefits'] = True
    
    # Show top companies by data quality
    sorted_companies = sorted(company_stats.items(), 
                            key=lambda x: x[1]['fields_populated'] / x[1]['total_jobs'], 
                            reverse=True)
    
    print(f"   Top companies by data quality:")
    for company, stats in sorted_companies[:10]:
        avg_fields = stats['fields_populated'] / stats['total_jobs']
        print(f"     {company:25}: {avg_fields:.1f} fields/job, salary: {'✅' if stats['has_salary'] else '❌'}, benefits: {'✅' if stats['has_benefits'] else '❌'}")

if __name__ == "__main__":
    asyncio.run(analyze_greenhouse_patterns())
