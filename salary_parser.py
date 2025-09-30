import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class SalaryRange:
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
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
        # Annual salary indicators (high priority)
        self.annual_indicators = [
            'annually', 'annual', 'per year', 'yearly', '/year', 'yr',
            'base salary', 'base compensation', 'total compensation', 'total comp',
            'salary range', 'compensation range', 'pay range', 'compensation:',
            'salary:', 'base:', 'compensation'
        ]
        
        # Hourly rate indicators (low priority - should be avoided)
        self.hourly_indicators = [
            'per hour', 'hourly', '/hour', 'hr', 'hourly rate',
            'rate:', 'pay rate', 'wage'
        ]
        
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
        
    
    def parse_salary(self, text: str) -> SalaryRange:
        """Parse salary information from text, prioritizing annual salaries"""
        if not text or text.strip().lower() in ['null', 'none', '']:
            return SalaryRange(raw_text=text)
        
        text = text.strip()
        salary_range = SalaryRange(raw_text=text)
        text_lower = text.lower()
        
        # First, try to find annual salary patterns
        annual_matches = self._find_annual_salaries(text)
        if annual_matches:
            # Use the first (best) annual salary match
            best_match = annual_matches[0]
            if best_match['is_range']:
                salary_range.min_salary = best_match['min_salary']
                salary_range.max_salary = best_match['max_salary']
                salary_range.is_range = True
            else:
                salary_range.min_salary = best_match['min_salary']
                salary_range.is_range = False
            return salary_range
        
        # If no annual salary found, try general patterns but avoid hourly rates
        general_matches = self._find_general_salaries(text)
        if general_matches:
            # Filter out hourly rates
            non_hourly_matches = [m for m in general_matches if not self._is_likely_hourly(m, text)]
            if non_hourly_matches:
                best_match = non_hourly_matches[0]
                if best_match['is_range']:
                    salary_range.min_salary = best_match['min_salary']
                    salary_range.max_salary = best_match['max_salary']
                    salary_range.is_range = True
                else:
                    salary_range.min_salary = best_match['min_salary']
                    salary_range.is_range = False
        
        return salary_range
    
    def _find_annual_salaries(self, text: str) -> List[Dict]:
        """Find salary patterns that are clearly annual"""
        matches = []
        text_lower = text.lower()
        
        # Look for patterns near annual indicators
        for pattern_name, pattern in self.patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Check if this match is near an annual indicator
                start, end = match.span()
                context_start = max(0, start - 50)
                context_end = min(len(text), end + 50)
                context = text[context_start:context_end].lower()
                
                # Check if context contains annual indicators
                has_annual_context = any(indicator in context for indicator in self.annual_indicators)
                has_hourly_context = any(indicator in context for indicator in self.hourly_indicators)
                
                # Prioritize annual context, but don't exclude if there's also hourly context
                if has_annual_context:
                    if 'range' in pattern_name:
                        min_val, max_val = match.groups()
                        if 'k_notation' in pattern_name:
                            min_salary = self._parse_number(min_val + 'K')
                            max_salary = self._parse_number(max_val + 'K')
                        else:
                            min_salary = self._parse_number(min_val)
                            max_salary = self._parse_number(max_val)
                        
                        matches.append({
                            'min_salary': min_salary,
                            'max_salary': max_salary,
                            'is_range': True,
                            'priority': 1,  # High priority for annual
                            'context': context
                        })
                    else:
                        if 'k_notation' in pattern_name:
                            min_salary = self._parse_number(match.group(1) + 'K')
                        else:
                            min_salary = self._parse_number(match.group(1))
                        
                        matches.append({
                            'min_salary': min_salary,
                            'is_range': False,
                            'priority': 1,  # High priority for annual
                            'context': context
                        })
        
        # Sort by priority (higher first)
        matches.sort(key=lambda x: x['priority'], reverse=True)
        return matches
    
    def _find_general_salaries(self, text: str) -> List[Dict]:
        """Find general salary patterns when no annual context is found"""
        matches = []
        
        for pattern_name, pattern in self.patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if 'range' in pattern_name:
                    min_val, max_val = match.groups()
                    if 'k_notation' in pattern_name:
                        min_salary = self._parse_number(min_val + 'K')
                        max_salary = self._parse_number(max_val + 'K')
                    else:
                        min_salary = self._parse_number(min_val)
                        max_salary = self._parse_number(max_val)
                    
                    matches.append({
                        'min_salary': min_salary,
                        'max_salary': max_salary,
                        'is_range': True,
                        'priority': 0,  # Lower priority for general
                        'context': text[max(0, match.start()-20):min(len(text), match.end()+20)].lower()
                    })
                else:
                    if 'k_notation' in pattern_name:
                        min_salary = self._parse_number(match.group(1) + 'K')
                    else:
                        min_salary = self._parse_number(match.group(1))
                    
                    matches.append({
                        'min_salary': min_salary,
                        'is_range': False,
                        'priority': 0,  # Lower priority for general
                        'context': text[max(0, match.start()-20):min(len(text), match.end()+20)].lower()
                    })
        
        return matches
    
    def _is_likely_hourly(self, match: Dict, text: str) -> bool:
        """Check if a salary match is likely an hourly rate"""
        context = match['context']
        
        # Check for hourly indicators in context
        has_hourly_context = any(indicator in context for indicator in self.hourly_indicators)
        
        # Check if the amount is suspiciously low for annual salary
        min_salary = match.get('min_salary', 0)
        if min_salary < 20000:  # Less than $20k is likely hourly
            return True
        
        # If it has hourly context, it's likely hourly
        if has_hourly_context:
            return True
            
        # If it's a very small amount and near hourly indicators, it's likely hourly
        if min_salary < 100 and any(indicator in context for indicator in ['hour', 'hr', 'rate']):
            return True
        
        return False
    
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
    
    def has_only_hourly_rates(self, text: str) -> bool:
        """Check if the text contains only hourly rates (no annual salary)"""
        if not text or text.strip().lower() in ['null', 'none', '']:
            return False  # No salary data is fine, don't skip
        
        text_lower = text.lower()
        
        # First check if there are any annual salary indicators
        has_annual_indicators = any(indicator in text_lower for indicator in self.annual_indicators)
        
        # If there are annual indicators, it's not hourly-only
        if has_annual_indicators:
            return False
        
        # Check if there are any salary patterns
        general_matches = self._find_general_salaries(text)
        if not general_matches:
            return False  # No salary patterns found, don't skip
        
        # Check if there are hourly indicators
        has_hourly_indicators = any(indicator in text_lower for indicator in self.hourly_indicators)
        
        # If there are hourly indicators but no annual indicators, it's hourly-only
        if has_hourly_indicators:
            return True
        
        # Check if all salary patterns look like hourly rates
        all_hourly = all(self._is_likely_hourly(match, text) for match in general_matches)
        if all_hourly:
            return True
        
        return False
    
    def should_skip_job(self, text: str) -> bool:
        """Determine if a job should be skipped based on salary data"""
        return self.has_only_hourly_rates(text)

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
