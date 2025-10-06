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
        """Parse Greenhouse job posting using AI"""
        
        # Truncate content to avoid token limits (keep first 4000 chars)
        truncated_content = raw_content[:4000]
        
        prompt = f"""
You are an expert at parsing job postings. Extract structured information from this Greenhouse job posting.

Job URL: {job_url}
Raw Content: {truncated_content}

Extract and return ONLY a JSON object with these exact fields:
{{
    "title": "Job title (clean, no extra text)",
    "company": "Company name (clean, no extra text)", 
    "location": "Primary location (city, state/country)",
    "alternate_locations": "Other locations as comma-separated string (or null if none)",
    "employment_type": "Full-time, Part-time, Contract, Internship, etc.",
    "description": "Clean job description (remove navigation, forms, etc.)",
    "requirements": "Required qualifications and skills",
    "responsibilities": "Job duties and responsibilities", 
    "benefits": "Benefits and perks offered",
    "salary_range": "Salary information if mentioned (or null)",
    "experience_level": "Entry, Mid, Senior, Executive, or null if unclear",
    "work_environment": "Remote, Hybrid, Onsite, or null if unclear"
}}

Rules:
- Return ONLY valid JSON, no other text
- Use null for missing information
- Clean up text (remove extra whitespace, navigation elements)
- For location: extract the main location, put others in alternate_locations
- For description: remove company boilerplate, focus on actual job content
- Be precise and accurate
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            # Parse the JSON response
            result = json.loads(response.choices[0].message.content)
            
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