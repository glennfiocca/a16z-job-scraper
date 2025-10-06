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
    "about_company": "Copy the VERBATIM text about the company from the listing - company description, mission, what they do, their story, etc. This is usually in an 'About Us' or 'About the Company' section. It is typically toward the top of listings, as well. Do not summarize.", 
    "location": "Primary location (city, state/country). Can be remote, but only for fully-remote jobs that do not have a location listed.",
    "alternate_locations": "Other locations as comma-separated string (or null if none). Remote can be listed here if it is an option.",
    "employment_type": "Full-time, Part-time, Contract, Internship, etc. Almost all jobs should be full-time, under the current scraping logic.",
    "about_job": "Copy ALL job role content VERBATIM including 'About the Role'/'About this role' intro paragraphs AND all responsibilities/day-to-day tasks. This field should contain both the general job description and what the candidate will do. Include sections like 'What You'll Do', 'Responsibilities', 'Key Responsibilities', etc. DO NOT include qualifications in this field.",
    "qualifications": "Copy ALL qualifications/requirements VERBATIM from sections like 'About You', 'Requirements', 'Qualifications', 'What we're looking for', etc. Include exact text with all bullet points. DO NOT duplicate this content in the about_job field above.",
    "benefits": "Copy ALL benefits and perks VERBATIM from the listing - exact text including all details about equity, insurance, PTO, allowances, etc. Do not summarize.",
    "salary_range": "COMPLETE salary range exactly as written (e.g. '$180K - $260K + equity'). Include equity/stock info if mentioned.",
    "work_environment": "Remote, Hybrid, Onsite, or null if unclear"
}}

CRITICAL EXTRACTION RULES - ZERO DUPLICATION ALLOWED:
- Copy text EXACTLY as written - DO NOT summarize, paraphrase, or reword
- **ZERO DUPLICATION**: Each sentence/bullet point appears in ONLY ONE field, never repeated
- **STRICT SEGMENTATION RULES**:
  * about_job = ALL role overview + what the job generally entails + responsibilities + day-to-day tasks
  * qualifications = ONLY qualifications + skills needed + experience required
- **IMPORTANT - "About You" sections ALWAYS go in qualifications, NEVER in about_job**
- **IMPORTANT - If a section describes what skills/qualifications are needed, it goes in qualifications ONLY, not about_job**
- For about_job: Extract ALL content about the job role including high-level description AND specific responsibilities/tasks. Include 'About the Role', 'What You'll Do', 'Responsibilities', 'Key Responsibilities', etc.
- For qualifications: Extract ALL "About You", "Requirements", "Qualifications", "What we're looking for", "You have", "You are" sections
- **VERIFICATION STEP**: Before finalizing, check that NO text appears in both about_job and qualifications. If it does, remove it from the less relevant field
- For benefits: Copy ENTIRE benefits section verbatim
- Return ONLY valid JSON
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=4000  # Increased to capture complete job descriptions including Key Responsibilities sections
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
            "about_job": None,
            "qualifications": None,
            "benefits": None,
            "salary_range": None,
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