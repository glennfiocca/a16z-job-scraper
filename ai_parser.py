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
You are an expert at extracting information from job postings. Extract the EXACT TEXT from the listing - DO NOT SUMMARIZE OR PARAPHRASE.

Job URL: {job_url}
Raw Content: {truncated_content}

Extract and return ONLY a JSON object with these exact fields:
{{
    "title": "Job title (clean, no extra text)",
    "company": "Company name (clean, no extra text)",
    "about_company": "Copy the VERBATIM text about the company from the listing - company description, mission, what they do, their story, etc. This is usually in an 'About Us' or 'About the Company' section. Do not summarize.", 
    "location": "Primary location (city, state/country)",
    "alternate_locations": "Other locations as comma-separated string (or null if none)",
    "employment_type": "Full-time, Part-time, Contract, Internship, etc.",
    "description": "Copy the EXACT job description text from the listing - word for word, no summarizing",
    "requirements": "Copy ALL requirements VERBATIM from the listing - exact text, bullet points, everything as written. Do not summarize or paraphrase.",
    "responsibilities": "Copy ALL responsibilities VERBATIM from the listing - exact text as written, preserve all details and bullet points. Do not summarize.", 
    "benefits": "Copy ALL benefits and perks VERBATIM from the listing - exact text including all details about equity, insurance, PTO, allowances, etc. Do not summarize.",
    "salary_range": "COMPLETE salary range exactly as written (e.g. '$180K - $260K + equity'). Include equity/stock info if mentioned.",
    "experience_level": "Entry, Mid, Senior, Executive, or null if unclear",
    "work_environment": "Remote, Hybrid, Onsite, or null if unclear"
}}

CRITICAL EXTRACTION RULES - VERBATIM TEXT ONLY:
- Copy text EXACTLY as written in the job posting - DO NOT summarize, paraphrase, or reword
- Extract COMPLETE sections word-for-word from the original listing
- Preserve ALL details, bullet points, and specific information exactly as they appear
- For requirements: Copy the ENTIRE requirements section verbatim - every qualification, skill, year requirement exactly as written
- For responsibilities: Copy the ENTIRE responsibilities section verbatim - every duty and task exactly as written  
- For benefits: Copy the ENTIRE benefits section verbatim - every perk, detail, and number exactly as written
- Remove only navigation/UI elements and footer text - keep ALL job content unchanged
- If information is formatted as bullet points, preserve that structure in the text
- Return ONLY valid JSON, no other text
- Use null only if that section truly does not exist in the listing
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
            "about_company": None,
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