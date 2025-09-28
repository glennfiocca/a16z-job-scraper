import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class SalaryRange:
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    currency: str = "USD"
    period: str = "yearly"  # yearly, hourly, monthly
    is_range: bool = False
    raw_text: str = ""
    
    def to_string(self) -> str:
        """Convert to standardized string format"""
        if not self.min_salary:
            return "Not specified"
        
        if self.is_range and self.max_salary:
            return f"${self.min_salary:,} - ${self.max_salary:,}"
        else:
            return f"${self.min_salary:,}"

class SalaryParser:
    def __init__(self):
        # Regex patterns for different salary formats (ordered by specificity)
        self.patterns = {
            # K notation ranges first (most specific)
            'range_k_notation': r'\$(\d{1,3})K\s*-\s*\$(\d{1,3})K',
            # K notation single (must not be followed by range)
            'single_k_notation': r'\$(\d{1,3})K(?!\s*-\s*\$)',  
            # Regular ranges
            'range_with_commas': r'\$(\d{1,3}(?:,\d{3})*)\s*-\s*\$(\d{1,3}(?:,\d{3})*)',
            'range_no_commas': r'\$(\d{3,7})\s*-\s*\$(\d{3,7})',
            'range_with_to': r'\$(\d{1,3}(?:,\d{3})*)\s+to\s+\$(\d{1,3}(?:,\d{3})*)',
            # Single salaries (less specific, comes last)
            'single_with_commas': r'\$(\d{1,3}(?:,\d{3})*)(?!K)',  # Not followed by K
            'single_no_commas': r'\$(\d{3,7})(?!K)',  # Not followed by K
        }
        
        # Period indicators
        self.period_indicators = {
            'yearly': ['per year', 'annually', 'yearly', '/year', 'yr'],
            'hourly': ['per hour', 'hourly', '/hour', 'hr'],
            'monthly': ['per month', 'monthly', '/month']
        }
    
    def parse_salary(self, text: str) -> SalaryRange:
        """Parse salary information from text"""
        if not text or text.strip().lower() in ['null', 'none', '']:
            return SalaryRange(raw_text=text)
        
        text = text.strip()
        salary_range = SalaryRange(raw_text=text)
        
        # Detect period
        text_lower = text.lower()
        for period, indicators in self.period_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                salary_range.period = period
                break
        
        # Try different patterns in order of specificity
        for pattern_name, pattern in self.patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'range' in pattern_name:
                    min_val, max_val = match.groups()
                    # Handle K notation specially
                    if 'k_notation' in pattern_name:
                        salary_range.min_salary = self._parse_number(min_val + 'K')
                        salary_range.max_salary = self._parse_number(max_val + 'K')
                    else:
                        salary_range.min_salary = self._parse_number(min_val)
                        salary_range.max_salary = self._parse_number(max_val)
                    salary_range.is_range = True
                else:
                    # Handle K notation specially
                    if 'k_notation' in pattern_name:
                        salary_range.min_salary = self._parse_number(match.group(1) + 'K')
                    else:
                        salary_range.min_salary = self._parse_number(match.group(1))
                    salary_range.is_range = False
                break
        
        return salary_range
    
    def _parse_number(self, num_str: str) -> int:
        """Parse number string, handling commas and K notation"""
        # Handle K notation first
        if num_str.upper().endswith('K'):
            return int(num_str[:-1]) * 1000
        
        # Remove commas for regular numbers
        num_str = num_str.replace(',', '')
        return int(num_str)
    
    def standardize_salary_range(self, text: str) -> str:
        """Standardize salary range to consistent format"""
        salary_range = self.parse_salary(text)
        return salary_range.to_string()

# Example usage and testing
def test_salary_parser():
    parser = SalaryParser()
    
    test_cases = [
        "$180,000 - $231,000",
        "$180000 - $231000", 
        "$180,000",
        "$180K - $231K",
        "$180K",
        "This Base Compensation...",
        "NULL",
        "$180,000 to $231,000",
        "$180,000 per year",
        "$50 per hour"
    ]
    
    print("Salary Standardization Test Results:")
    print("=" * 50)
    
    for test_case in test_cases:
        result = parser.standardize_salary_range(test_case)
        print(f"Input:  {test_case}")
        print(f"Output: {result}")
        print("-" * 30)

if __name__ == "__main__":
    test_salary_parser()
