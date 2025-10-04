#!/usr/bin/env python3
"""
Enhanced Greenhouse job parsing with robust field extraction
Based on analysis of 30 sample jobs across different companies
"""

import re
import asyncio
from playwright.async_api import async_playwright

class EnhancedGreenhouseParser:
    def __init__(self):
        # Employment type filtering patterns
        self.employment_type_patterns = {
            'contract': [
                r'\bcontract\b', r'\btemporary\b', r'\btemp\b', r'\bfreelance\b',
                r'\bconsultant\b', r'\bpart.?time\b', r'\binternship\b', r'\bintern\b',
                r'\bapprentice\b', r'\bco.?op\b', r'\bseasonal\b', r'\bhourly\b'
            ],
            'full_time': [
                r'\bfull.?time\b', r'\bpermanent\b', r'\bsalaried\b', r'\bexempt\b'
            ]
        }
        
        # Work environment detection patterns
        self.work_environment_patterns = {
            'remote': [
                r'\bremote\b', r'\bwork from home\b', r'\bwfh\b', r'\bdistributed\b',
                r'\bvirtual\b', r'\btelecommute\b', r'\bfully remote\b', r'\b100% remote\b'
            ],
            'hybrid': [
                r'\bhybrid\b', r'\bmix of remote and office\b', r'\bflexible\b',
                r'\bpartially remote\b', r'\bremote first\b', r'\boffice optional\b'
            ],
            'in_office': [
                r'\bon.?site\b', r'\bin.?office\b', r'\bon.?premises\b', r'\boffice\b',
                r'\blocation\b', r'\bheadquarters\b', r'\bworkspace\b'
            ]
        }
        
        # Enhanced section headers for better parsing
        self.section_headers = {
            'responsibilities': [
                'what you\'ll do', 'what you will do', 'you will', 'responsibilities',
                'duties', 'key responsibilities', 'role description', 'what you do',
                'about the job', 'the opportunity', 'about this role', 'key responsibilities',
                'what you\'ll be doing', 'what you will be doing', 'role overview',
                'position overview', 'job overview', 'responsibility', 'what we need',
                'your role', 'you\'ll be responsible for', 'you will be responsible for'
            ],
            'requirements': [
                'required qualifications', 'requirements', 'you should have',
                'you have', 'qualifications', 'required skills', 'minimum qualifications',
                'preferred qualifications', 'nice to have', 'bonus points',
                'we\'d love to hear from you if you have', 'minimum qualifications',
                'preferred qualifications', 'qualifications', 'you should have',
                'required experience', 'experience required', 'skills required',
                'what we\'re looking for', 'ideal candidate', 'candidate requirements',
                'must have', 'should have', 'required', 'preferred', 'desired'
            ],
            'benefits': [
                'benefits', 'what we offer', 'perks', 'compensation', 'package',
                'healthcare benefits', 'additional benefits', 'retirement savings plan',
                'income protection', 'generous time off', 'family planning',
                'mental health resources', 'professional development',
                'pay transparency disclosure', 'annual base salary range',
                'in addition to salary', 'comprehensive benefits', 'benefits package',
                'what you can expect', 'compensation and benefits', 'total rewards',
                'employee benefits', 'company benefits', 'work benefits',
                'health insurance', 'dental', 'vision', 'pto', 'vacation',
                'stock options', 'equity', '401k', 'retirement', 'insurance'
            ]
        }
        
        # Salary parsing patterns
        self.salary_patterns = [
            r'\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
            r'\$?([\d,]+)K\s*[-–—]\s*\$?([\d,]+)K\s*USD?',
            r'\$?([\d,]+)\s*to\s*\$?([\d,]+)\s*USD?',
            r'\$?([\d,]+)K\s*to\s*\$?([\d,]+)K\s*USD?',
            r'US Salary Range[:\s]*\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
            r'Annual Base Salary Range[:\s]*\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
            r'Salary Range[:\s]*\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
            r'Compensation[:\s]*\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
            r'Pay Range[:\s]*\$?([\d,]+)\s*[-–—]\s*\$?([\d,]+)\s*USD?',
            r'\$([\d,]+)\s*[-–—]\s*\$([\d,]+)',
            r'\$([\d,]+)\s*to\s*\$([\d,]+)',
            r'Salary Range\s*\$([\d,]+)\s*[-–—]\s*\$([\d,]+)',
            r'Compensation\s*\$([\d,]+)\s*[-–—]\s*\$([\d,]+)'
        ]

    def should_filter_job(self, job_data):
        """Determine if job should be filtered out based on employment type"""
        title = job_data.get('title', '').lower()
        description = job_data.get('description', '').lower()
        content = f"{title} {description}"
        
        # Check for contract/part-time indicators
        for pattern in self.employment_type_patterns['contract']:
            if re.search(pattern, content, re.IGNORECASE):
                return True, f"Filtered: Found contract indicator '{pattern}'"
        
        return False, "Passed employment type filter"

    def extract_work_environment(self, content):
        """Extract work environment with robust pattern matching"""
        content_lower = content.lower()
        
        # Check for remote work indicators
        for pattern in self.work_environment_patterns['remote']:
            if re.search(pattern, content_lower):
                return 'remote'
        
        # Check for hybrid work indicators
        for pattern in self.work_environment_patterns['hybrid']:
            if re.search(pattern, content_lower):
                return 'hybrid'
        
        # Check for in-office indicators
        for pattern in self.work_environment_patterns['in_office']:
            if re.search(pattern, content_lower):
                return 'in-office'
        
        return 'in-office'  # Default assumption

    def extract_salary_info(self, content):
        """Extract salary information with enhanced pattern matching"""
        salary_info = {'salary_range': 'Not provided', 'salary_min': None, 'salary_max': None}
        
        for pattern in self.salary_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                min_salary = match.group(1).replace(',', '')
                max_salary = match.group(2).replace(',', '')
                
                # Handle K notation
                if 'K' in match.group(0).upper():
                    min_salary = str(int(min_salary) * 1000)
                    max_salary = str(int(max_salary) * 1000)
                
                salary_info['salary_range'] = f"${min_salary} - ${max_salary}"
                salary_info['salary_min'] = int(min_salary)
                salary_info['salary_max'] = int(max_salary)
                break
        
        return salary_info

    def parse_sections_enhanced(self, content):
        """Enhanced section parsing with better pattern matching"""
        sections = {}
        lines = content.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # Check if this line is a section header
            line_lower = line_clean.lower()
            found_section = None
            
            for section_key, keywords in self.section_headers.items():
                if any(keyword in line_lower for keyword in keywords):
                    # Save previous section
                    if current_section and section_content:
                        sections[current_section] = '\n'.join(section_content)[:2000]
                    
                    current_section = section_key
                    section_content = []
                    found_section = True
                    break
            
            if not found_section and current_section:
                # Skip lines that are clearly not part of the current section
                skip_indicators = [
                    'create a job alert', 'apply for this job', 'indicates a required field',
                    'first name', 'last name', 'email', 'phone', 'resume', 'cover letter',
                    'submit application', 'privacy policy', 'candidate data privacy',
                    'applicant-privacy-notice', 'voluntary self-identification',
                    'equal employment opportunity', 'global data privacy notice',
                    'commitment to equal opportunity', 'by applying for this job',
                    'back to jobs', 'apply', 'powered by', 'greenhouse',
                    'read our privacy policy', 'don\'t check off every box',
                    'studies have shown', 'waymark is dedicated',
                    'you may be just the right candidate', 'interested in building your career',
                    'get future opportunities sent straight to your email'
                ]
                
                if not any(indicator in line_lower for indicator in skip_indicators):
                    section_content.append(line_clean)
        
        # Save the last section
        if current_section and section_content:
            sections[current_section] = '\n'.join(section_content)[:2000]
        
        return sections

    async def extract_job_enhanced(self, page, job_data):
        """Enhanced job extraction with improved parsing"""
        try:
            # Basic job info
            title = await page.query_selector('h1, .job-title, [data-qa="job-title"]')
            if title:
                job_data['title'] = await title.inner_text()
            
            # Location extraction
            location_selectors = [
                '.location', '[data-mapped="location"]', '.job-location',
                '.location-info', '.job-location-info', '[class*="location"]',
                '[data-location]', '.office-location', '.work-location'
            ]
            
            location = await self.get_text_by_selectors(page, location_selectors)
            if location:
                job_data['location'] = location
            
            # Employment type - always set to Full time for now
            job_data['employment_type'] = 'Full time'
            
            # Extract content
            content_element = await page.query_selector('main')
            if not content_element:
                content_element = await page.query_selector('body')
            
            if content_element:
                full_content = await content_element.inner_text()
                
                # Clean content
                lines = full_content.split('\n')
                cleaned_lines = []
                
                skip_initial_phrases = ['Back to jobs', 'Apply']
                in_job_content = False
                
                for line in lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    
                    # Skip initial navigation elements
                    if not in_job_content and any(phrase in line_clean for phrase in skip_initial_phrases):
                        continue
                    
                    # Mark that we've started processing job content
                    if not in_job_content and any(phrase in line_clean.lower() for phrase in ['about', 'waymark', 'community health', 'job', 'role']):
                        in_job_content = True
                    
                    # Stop at application forms and job alerts
                    if in_job_content and any(phrase in line_clean for phrase in [
                        'Create a Job Alert', 'Apply for this job', 'indicates a required field',
                        'First Name', 'Last Name', 'Email', 'Phone', 'Resume', 'Cover Letter',
                        'Submit Application', 'Powered by', 'Privacy Policy',
                        'Don\'t check off every box', 'Studies have shown',
                        'Waymark is dedicated', 'You may be just the right candidate'
                    ]):
                        break
                    
                    if in_job_content:
                        cleaned_lines.append(line_clean)
                
                full_content = '\n'.join(cleaned_lines)
                job_data['description'] = full_content[:10000]
                
                # Enhanced section parsing
                sections = self.parse_sections_enhanced(full_content)
                job_data.update(sections)
                
                # Work environment extraction
                job_data['work_environment'] = self.extract_work_environment(full_content)
                
                # Salary extraction
                salary_info = self.extract_salary_info(full_content)
                job_data.update(salary_info)
            
            # Check if job should be filtered
            should_filter, reason = self.should_filter_job(job_data)
            if should_filter:
                return None, reason
            
            return job_data, "Success"
            
        except Exception as e:
            return None, f"Error: {e}"

    async def get_text_by_selectors(self, page, selectors):
        """Get text by trying multiple selectors"""
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()
            except:
                continue
        return None

# Test the enhanced parser
async def test_enhanced_parser():
    """Test the enhanced parser on a few sample jobs"""
    parser = EnhancedGreenhouseParser()
    
    test_urls = [
        "https://job-boards.greenhouse.io/waymark/jobs/4595277005",
        "https://job-boards.greenhouse.io/andurilindustries/jobs/4925653007?gh_jid=4925653007",
        "https://job-boards.greenhouse.io/appliedintuition/jobs/4376428005?gh_jid=4376428005"  # Contract job
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for i, url in enumerate(test_urls, 1):
            try:
                print(f"\n🧪 Testing enhanced parser {i}/3: {url}")
                
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                company_name = url.split('/')[-3] if 'greenhouse.io' in url else 'Unknown'
                job_data = {'url': url, 'company': company_name}
                
                result, status = await parser.extract_job_enhanced(page, job_data)
                
                if result:
                    print(f"   ✅ Success: {result.get('title', 'Unknown Title')}")
                    print(f"   📍 Location: {result.get('location', 'Not found')}")
                    print(f"   💼 Employment: {result.get('employment_type', 'Not found')}")
                    print(f"   🏢 Work Env: {result.get('work_environment', 'Not found')}")
                    print(f"   💰 Salary: {result.get('salary_range', 'Not found')}")
                    print(f"   📝 Sections: {[k for k in ['responsibilities', 'requirements', 'benefits'] if result.get(k)]}")
                else:
                    print(f"   ❌ Filtered: {status}")
                
                await page.close()
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_enhanced_parser())
