#!/usr/bin/env python3
"""
Test script to verify salary parsing is working correctly
"""

from salary_parser import SalaryParser

def test_salary_parsing():
    """Test the salary parser with various inputs"""
    parser = SalaryParser()
    
    test_cases = [
        "$180,000 - $231,000",
        "$180000 - $231000", 
        "$180,000",
        "$180K - $231K",
        "$180K",
        "$50,000 - $80,000 per year",
        "$25 per hour",
        "Not provided",
        "NULL",
        "",
        "$146,000 - $194,000"
    ]
    
    print("🧪 Testing Salary Parser")
    print("=" * 60)
    
    for test_case in test_cases:
        print(f"\n📝 Input: '{test_case}'")
        
        # Test standardization
        standardized = parser.standardize_salary_range(test_case)
        print(f"   Standardized: {standardized}")
        
        # Test parsing for min/max
        salary_data = parser.parse_salary(test_case)
        print(f"   Min Salary: {salary_data.min_salary}")
        print(f"   Max Salary: {salary_data.max_salary}")
        print(f"   Is Range: {salary_data.is_range}")
        
        # Test if should skip (hourly only)
        should_skip = parser.should_skip_job(test_case)
        print(f"   Should Skip: {should_skip}")
        
        print("-" * 40)

if __name__ == "__main__":
    test_salary_parsing()






