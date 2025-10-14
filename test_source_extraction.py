#!/usr/bin/env python3
"""
Test script to verify source extraction is working correctly
"""

from main import extract_source_from_url

def test_source_extraction():
    """Test the source extraction function with various URLs"""
    
    test_cases = [
        ("https://jobs.ashbyhq.com/company/job-id", "Ashby"),
        ("https://boards.greenhouse.io/company/job-id", "Greenhouse"),
        ("https://jobs.lever.co/company/job-id", "Lever"),
        ("https://company.wd12.myworkdayjobs.com/job-id", "Workday"),
        ("https://jobs.smartrecruiters.com/company/job-id", "SmartRecruiters"),
        ("https://apply.workable.com/company/job-id", "Workable"),
        ("https://stripe.com/jobs/job-id", "Stripe"),
        ("https://databricks.com/careers/job-id", "Databricks"),
        ("https://waymo.com/careers/job-id", "Waymo"),
        ("https://navan.com/careers/job-id", "Navan"),
        ("https://wiz.io/careers/job-id", "Wiz"),
        ("https://fivetran.com/careers/job-id", "Fivetran"),
        ("https://unknown-platform.com/jobs/job-id", "Unknown-platform"),
        ("https://example.com/job", "Other")
    ]
    
    print("🧪 Testing Source Extraction")
    print("=" * 60)
    
    for url, expected in test_cases:
        result = extract_source_from_url(url)
        status = "✅" if result == expected else "❌"
        print(f"{status} URL: {url}")
        print(f"   Expected: {expected}")
        print(f"   Got:      {result}")
        print("-" * 40)

if __name__ == "__main__":
    test_source_extraction()





