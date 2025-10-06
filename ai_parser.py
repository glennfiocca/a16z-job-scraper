import os
import json
import asyncio
from openai import AsyncOpenAI
from typing import Dict, Any, Optional

class AIParser:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set. Please add it as a secret in Replit.")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"  # Start with cheaper model, can upgrade to gpt-4 later
        
    async def parse_greenhouse_job(self, raw_content: str, job_url: str) -> Dict[str, Any]:
        """Parse job posting using AI with comprehensive extraction"""
        
        # Increase limit to 10000 chars to capture more content
        truncated_content = raw_content[:10000]
        
        prompt = f"""
You are an expert at extracting ALL information from job postings. Be COMPREHENSIVE and DETAILED.

Job URL: {job_url}
Raw Content: {truncated_content}

Extract and return ONLY a JSON object with these exact fields:
{{
    "title": "Job title (clean, no extra text)",
    "company": "Company name (clean, no extra text)", 
    "location": "Primary location (city, state/country)",
    "alternate_locations": "Other locations as comma-separated string (or null if none)",
    "employment_type": "Full-time, Part-time, Contract, Internship, etc.",
    "description": "COMPLETE job description - include role overview, team info, and what the job entails",
    "requirements": "ALL required qualifications, skills, experience, education - be exhaustive and detailed. Include years of experience, specific technologies, domain expertise, soft skills, etc.",
    "responsibilities": "ALL job duties and responsibilities - be detailed and complete. List everything the person will do.", 
    "benefits": "ALL benefits, perks, compensation details beyond base salary (equity, 401k, healthcare, PTO, work from home, childcare, wellness, etc.) - be comprehensive",
    "salary_range": "COMPLETE salary range (e.g. '$180K - $260K', not just one number). Include equity/stock info if mentioned. If only one number shown, use that.",
    "experience_level": "Entry, Mid, Senior, Executive, or null if unclear",
    "work_environment": "Remote, Hybrid, Onsite, or null if unclear"
}}

CRITICAL EXTRACTION RULES:
- Extract EVERYTHING from each section - be thorough and comprehensive
- For requirements: Include ALL bullets, qualifications, years of experience, technologies, domains, education requirements
- For responsibilities: Include ALL duties, tasks, and what the person will actually do
- For benefits: Include ALL perks, equity, insurance, PTO, allowances, retirement, parental leave, etc.
- For salary_range: Capture FULL range like "$180K - $260K" or "$180K - $260K + equity", NOT just "$180K"
- Remove only navigation/UI elements, keep ALL substantive job content
- Return ONLY valid JSON, no other text
- Use null only if truly no information exists
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000  # Increased from 1000 to allow more comprehensive responses
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from AI")
            
            result = json.loads(content)
            
            # Validate required fields
            if not result.get('title') or not result.get('company'):
                raise ValueError("Missing required fields: title or company")
                
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error for {job_url}: {e}")
            return self._get_fallback_result()
        except Exception as e:
            print(f"AI parsing error for {job_url}: {e}")
            return self._get_fallback_result()
    
    def _get_fallback_result(self) -> Dict[str, Any]:
        """Return empty result when AI parsing fails"""
        return {
            "title": None,
            "company": None,
            "location": None,
            "alternate_locations": None,
            "employment_type": None,
            "description": None,
            "requirements": None,
            "responsibilities": None,
            "benefits": None,
            "salary_range": None,
            "experience_level": None,
            "work_environment": None
        }
    
    async def parse_job_safe(self, raw_content: str, job_url: str, platform: str = "greenhouse") -> Dict[str, Any]:
        """Safely parse job with error handling and fallbacks"""
        try:
            if platform.lower() == "greenhouse":
                return await self.parse_greenhouse_job(raw_content, job_url)
            else:
                # For now, use greenhouse parser for all platforms
                return await self.parse_greenhouse_job(raw_content, job_url)
        except Exception as e:
            print(f"AI parsing failed for {job_url}: {e}")
            return self._get_fallback_result()

# Global instance - will be created when needed
ai_parser = None

def get_ai_parser():
    """Get or create AI parser instance"""
    global ai_parser
    if ai_parser is None:
        ai_parser = AIParser()
    return ai_parser