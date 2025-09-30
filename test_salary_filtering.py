#!/usr/bin/env python3
"""
Test script to demonstrate the new salary filtering functionality
"""

from salary_parser import SalaryParser

def test_salary_filtering():
    parser = SalaryParser()
    
    # Test cases representing different job scenarios
    test_cases = [
        # Jobs that should be KEPT (no salary data)
        {
            'title': 'Software Engineer',
            'company': 'Tech Corp',
            'salary_range': '',
            'expected': 'KEEP'
        },
        {
            'title': 'Data Scientist',
            'company': 'AI Startup',
            'salary_range': 'Competitive salary',
            'expected': 'KEEP'
        },
        
        # Jobs that should be KEPT (has annual salary)
        {
            'title': 'Senior Developer',
            'company': 'Big Tech',
            'salary_range': 'Base salary: $120,000 - $150,000 annually',
            'expected': 'KEEP'
        },
        {
            'title': 'Product Manager',
            'company': 'Startup Inc',
            'salary_range': 'Compensation: $100,000 - $130,000 per year',
            'expected': 'KEEP'
        },
        
        # Jobs that should be SKIPPED (only hourly rates)
        {
            'title': 'Part-time Developer',
            'company': 'Consulting Firm',
            'salary_range': 'Pay: $35/hour',
            'expected': 'SKIP'
        },
        {
            'title': 'Contractor',
            'company': 'Agency',
            'salary_range': 'Hourly rate: $50/hour',
            'expected': 'SKIP'
        },
        {
            'title': 'Freelancer',
            'company': 'Client Corp',
            'salary_range': 'Rate: $40/hour',
            'expected': 'SKIP'
        },
        
        # Jobs that should be KEPT (mixed compensation with annual salary)
        {
            'title': 'Full-time Engineer',
            'company': 'Tech Company',
            'salary_range': 'Base salary: $100,000 annually, plus $50/hour overtime',
            'expected': 'KEEP'
        },
        {
            'title': 'Senior Consultant',
            'company': 'Consulting',
            'salary_range': 'Compensation: $150,000 annually, $75/hour for extra work',
            'expected': 'KEEP'
        }
    ]
    
    print("🧪 Testing Salary Filtering Logic")
    print("=" * 60)
    print("This simulates what the scraper will do with different job listings")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        title = test_case['title']
        company = test_case['company']
        salary = test_case['salary_range']
        expected = test_case['expected']
        
        # Simulate the scraper's decision
        should_skip = parser.should_skip_job(salary) if salary else False
        actual = 'SKIP' if should_skip else 'KEEP'
        
        status = "✅" if actual == expected else "❌"
        
        print(f"{i:2d}. {status} {actual:4} | {title} at {company}")
        if salary:
            print(f"    Salary: {salary}")
        else:
            print(f"    Salary: (no salary data)")
        print()
    
    print("=" * 60)
    print("Summary:")
    print("- Jobs with no salary data: KEPT (we want these)")
    print("- Jobs with annual salary: KEPT (we want these)")
    print("- Jobs with only hourly rates: SKIPPED (we don't want these)")
    print("- Jobs with mixed compensation: KEPT (we extract the annual part)")

if __name__ == "__main__":
    test_salary_filtering()
