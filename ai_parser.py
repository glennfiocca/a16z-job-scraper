import os
import json
import asyncio
import re
from openai import AsyncOpenAI
from typing import Dict, Any, Optional

class AIParser:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set. Please add it as a secret in Replit.")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # More capable and cheaper than gpt-3.5-turbo
    
    @staticmethod
    def remove_emojis(text: str) -> str:
        """Remove all emojis from text"""
        if not text:
            return text
        # Emoji pattern - matches all emoji characters
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "]+", flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', text).strip()
        
    async def parse_greenhouse_job(self, raw_content: str, job_url: str) -> Dict[str, Any]:
        """Parse job posting using AI with comprehensive extraction"""
        
        # Increase limit to 10000 chars to capture more content
        truncated_content = raw_content[:10000]
        
        system_prompt = """You are an expert at extracting structured information from job postings.

SECTION MAPPING GUIDE - Different ATS platforms use different section headers:

ABOUT COMPANY (about_company field):
- Greenhouse/Lever: "About [Company]", "About Us", "Who We Are", "Company Overview"
- Ashby: "🚀 Join...", "About [Company]", company description paragraphs at the top
- General: Any introductory paragraphs describing the company's mission, products, culture, or history

ROLE/RESPONSIBILITIES (about_job field):
- Greenhouse/Lever: "About the Role", "The Role", "What You'll Do", "Responsibilities", "Key Responsibilities", "Day-to-Day"
- Ashby: "💻 Role", "💻 The Role", "What You'll Do"
- General: Bullet points or paragraphs describing daily tasks, duties, and what the person will do in this position

QUALIFICATIONS (qualifications field):
- Greenhouse/Lever: "About You", "Requirements", "Qualifications", "What We're Looking For", "You Have"
- Ashby: "👋 You", "What You Bring", "Requirements"
- General: Skills, experience, education requirements - what the candidate MUST HAVE

BENEFITS (benefits field):
- Greenhouse/Lever: "Benefits & Perks", "What We Offer", "Perks", "Benefits"
- Ashby: "🎁 Benefits", "💼 Perks", "What We Offer"
- General: Healthcare, PTO, retirement, perks, work-from-home allowances, parental leave, etc.

SALARY (salary_range field):
- Look for: "Compensation", "Salary Range", "$XXK - $YYK", "Base Salary", dollar amounts with "K" or "000"
- Ashby: "💸 Compensation", "💰 Salary" or under the "Compensation" section
- Important: Extract the ACTUAL salary numbers/range, not just "competitive" or "based on experience"
- Include equity mentions: "equity", "stock options", "RSUs" if part of the compensation

EXTRACTION RULES:
1. Copy text VERBATIM - do not summarize, paraphrase, or reword
2. Each field should capture its COMPLETE section, including all bullet points and paragraphs
3. about_job = What the job IS + What the person WILL DO (tasks, responsibilities, duties)
4. qualifications = What the candidate MUST HAVE (skills, experience, requirements)
5. Salary can appear in BOTH salary_range AND benefits - this is ALLOWED and EXPECTED
6. If a section has multiple paragraphs, include ALL of them
7. Preserve ALL bullet points - do not skip or omit any
8. REMOVE ALL EMOJIS from extracted text - no emojis should appear in any field (strip out 🚀 💻 👋 🎁 💸 💰 💼 💛 and all other emojis)

OUTPUT FORMAT:
Return ONLY a valid JSON object with these exact fields (no markdown, no explanation):
{
    "title": "exact job title",
    "company": "exact company name", 
    "about_company": "verbatim company description",
    "location": "primary city, state/country",
    "alternate_locations": "other locations as comma-separated string or null",
    "employment_type": "Full-time/Part-time/Contract/Internship",
    "about_job": "verbatim role description and ALL responsibilities",
    "qualifications": "verbatim requirements and qualifications", 
    "benefits": "verbatim complete benefits section",
    "salary_range": "exact salary range with equity info if mentioned",
    "work_environment": "Remote/Hybrid/Onsite or null"
}"""

        user_prompt = f"""Extract job information from this posting.

Job URL: {job_url}

EXTRACTION STEPS:
1. IDENTIFY sections by their headers (look for emoji headers on Ashby, text headers on others)
2. MAP each section to the correct JSON field using the Section Mapping Guide
3. COPY the complete section text verbatim into that field

Raw Job Content:
{truncated_content}

Extract and return the JSON object now:"""

        content = None
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from AI")
            
            # Clean up potential markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            
            # Validate required fields
            if not result.get('title') or not result.get('company'):
                raise ValueError("Missing required fields: title or company")
            
            # Remove emojis from all text fields
            text_fields = ['title', 'company', 'about_company', 'location', 'alternate_locations', 
                          'employment_type', 'about_job', 'qualifications', 'benefits', 
                          'salary_range', 'work_environment']
            
            for field in text_fields:
                if result.get(field) and isinstance(result[field], str):
                    result[field] = self.remove_emojis(result[field])
                
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error for {job_url}: {e}")
            if content:
                print(f"Raw response: {content[:500]}...")
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
