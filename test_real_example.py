#!/usr/bin/env python3
"""
Test the salary parser against real database examples
"""

from salary_parser import SalaryParser

def test_real_examples():
    parser = SalaryParser()
    
    # Real examples from your database
    test_cases = [
        # Your exact example
        """This Base Compensation pay range applies to our New York City located staff and may differ accord
New York Base Compensation Pay Range
$130,000 - $200,000 USD""",
        
        # Other common patterns we might see
        "Salary Range: $80,000 - $120,000 per year",
        "Compensation: $150,000 annually",
        "Pay: $60,000 - $80,000",
        "Base salary: $100,000",
        "Total compensation: $200,000 - $250,000",
        "Annual salary: $90,000",
        "This position offers $75,000 - $95,000",
        "We offer competitive compensation starting at $85,000",
        "Salary: $110,000 - $140,000 plus benefits",
    ]
    
    print("🧪 Testing Salary Parser with Real Database Examples")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Input:")
        print(f"   '{test_case}'")
        
        result = parser.standardize_salary_range(test_case)
        print(f"\n   Output: '{result}'")
        print("-" * 40)

if __name__ == "__main__":
    test_real_examples()

