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
            print("⚠️  OPENAI_API_KEY environment variable not set. AI parsing will be disabled.")
            self.client = None
            self.model = None
        else:
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
        
        # Check if AI parsing is available
        if not self.client:
            print("⚠️  AI parsing not available (no API key). Returning empty result.")
            return {
                "about_company": None,
                "about_job": None,
                "responsibilities": None,
                "qualifications": None,
                "benefits": None,
                "salary_range": None,
                "work_environment": None
            }
        
        # Increase limit to 10000 chars to capture more content
        truncated_content = raw_content[:10000]
        
        system_prompt = """You are an expert at extracting structured information from job postings.

SECTION MAPPING GUIDE - Different ATS platforms use different section headers:

ABOUT COMPANY (about_company field):
- Greenhouse/Lever: "About [Company]", "About Us", "Who We Are", "Company Overview"
- Ashby: "🚀 Join...", "About [Company]", company description paragraphs at the top
- General: Any introductory paragraphs describing the company's mission, products, culture, or history

ROLE DESCRIPTION (about_job field):
- This should be a PARAGRAPH describing what the role is about, the team, and the overall purpose
- Should NOT include bullet points - those go in responsibilities
- Examples: "This position is on the TRS Core Infrastructure team and will be focused on building the infrastructure to field TRS Products such as Altius, Ghost, Bolt and Anvil. Our charter is to provide the foundation for teams across Anduril to deploy cutting edge TRS autonomy and to tie it all together into an easy-to-use product."

RESPONSIBILITIES (responsibilities field):
- Greenhouse/Lever: "About the Role", "The Role", "What You'll Do", "Responsibilities", "Key Responsibilities", "Day-to-Day"
- Ashby: "💻 Role", "💻 The Role", "What You'll Do"
- General: Bullet points describing daily tasks, duties, and what the person will do in this position
- These should be formatted as bullet points with "• " prefix

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
3. about_job = PARAGRAPH describing what the role is about, the team, and overall purpose (NO bullet points)
4. responsibilities = BULLET POINTS describing specific tasks, duties, and what the person will do day-to-day
5. qualifications = What the candidate MUST HAVE (skills, experience, requirements)
6. Salary can appear in BOTH salary_range AND benefits - this is ALLOWED and EXPECTED
7. If a section has multiple paragraphs, include ALL of them
8. Preserve ALL bullet points - do not skip or omit any
9. REMOVE ALL EMOJIS from extracted text - no emojis should appear in any field (strip out 🚀 💻 👋 🎁 💸 💰 💼 💛 and all other emojis)

CRITICAL SEPARATION RULE:
- If you find a section that contains BOTH descriptive paragraphs AND bullet points, SEPARATE them:
  * Put the descriptive paragraph(s) in about_job field
  * Put the bullet points in responsibilities field
- Do NOT mix paragraphs and bullet points in the same field

CRITICAL BULLET POINT PRESERVATION RULES:
1. ALWAYS preserve existing bullet points from the source text
2. If source text has bullet points (•, *, -, etc.), convert them to "• " format
3. Each bullet point must be on a SEPARATE LINE with actual line breaks
4. Do NOT convert bullet points to paragraphs or run-on text

ABOUT_JOB FORMATTING:
- about_job should be a PARAGRAPH describing the role, team, and overall purpose
- If there are multiple descriptive paragraphs, join them with double newlines
- Do NOT include bullet points in about_job field - those go in responsibilities
- Example: "This position is on the Buyer Growth team and will be focused on driving top-of-funnel growth, first-time buyer success, acquisition, activation, and early retention. You'll partner with product, data, design, and marketing to build user experiences that drive growth."

RESPONSIBILITIES FORMATTING:
- responsibilities should be BULLET POINTS (not paragraphs)
- PRESERVE all bullet points from the source text
- Each responsibility should be a separate bullet point with "• " prefix
- Each bullet point must be on its own line
- Example:
• Lead and scale critical growth initiatives such as onboarding flows, referral systems, guest browsing, notification systems
• Design and own end-to-end systems, from backend services to frontend experiences, that impact millions of users
• Work across product, marketing, and data science to identify high-leverage growth opportunities and rapidly iterate on experiments
• Instrument, monitor, and improve funnels to drive measurable lifts in new user conversion and retention
• Mentor other engineers and contribute to raising the bar for engineering excellence across the team

QUALIFICATIONS FORMATTING:
- PRESERVE all bullet points from the source text
- Each requirement, skill, or qualification should be a separate bullet point on its own line
- Include both required and preferred qualifications as separate bullets
- Each bullet point must be on a separate line with "• " prefix
- Example format:
• 5+ years of full-time, generalist software engineering experience in high growth tech companies
• Bachelor's Degree in Computer Science or related field or equivalent work experience
• A strong foundation in backend and frontend development
• Excellent product instincts and ability to take ownership of ambiguous areas

BENEFITS FORMATTING:
- PRESERVE all bullet points from the source text
- Each benefit, perk, or offering should be a separate bullet point on its own line
- Each bullet point must be on a separate line with "• " prefix
- Example format:
• Flexible Time off Policy and Company-wide Holidays
• Health Insurance options including Medical, Dental, Vision
• Work From Home Support with home office setup allowance
• Care benefits including monthly wellness allowance and annual childcare allowance
• 401k offering for Traditional and Roth accounts in the US with employer match up to 4%
• 16 weeks of paid parental leave plus one month gradual return to work

OUTPUT FORMAT:
Return ONLY a valid JSON object with these exact fields (no markdown, no explanation):
{
    "title": "exact job title",
    "company": "exact company name", 
    "about_company": "verbatim company description",
    "location": "primary city, state/country",
    "alternate_locations": "other locations as comma-separated string or null",
    "employment_type": "Full-time/Part-time/Contract/Internship",
    "about_job": "paragraph description of the role, team, and overall purpose (NO bullet points)",
    "responsibilities": "bullet-pointed responsibilities and tasks with • prefix, each on separate line",
    "qualifications": "bullet-pointed requirements and qualifications with • prefix, each on separate line", 
    "benefits": "bullet-pointed complete benefits section with • prefix, each on separate line",
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
            
            # Post-process bullet point fields to ensure proper newline formatting
            bullet_fields = ['about_job', 'qualifications', 'benefits']
            for field in bullet_fields:
                if result.get(field):
                    content = result[field]
                    # Convert literal \n to actual newlines
                    content = content.replace('\\n', '\n')
                    # Also handle cases where \n might be escaped differently
                    content = content.replace('\\\\n', '\n')
                    # Fix bullet point formatting: ensure space after bullet and proper newlines
                    if '•' in content:
                        # Split by bullet points and reformat
                        parts = content.split('•')
                        if len(parts) > 1:
                            formatted_parts = []
                            for i, part in enumerate(parts):
                                if i == 0:
                                    # First part (before first bullet)
                                    if part.strip():
                                        formatted_parts.append(part.strip())
                                else:
                                    # Bullet point parts
                                    if part.strip():
                                        # Ensure space after bullet point
                                        clean_part = part.strip()
                                        if not clean_part.startswith(' '):
                                            clean_part = ' ' + clean_part
                                        formatted_parts.append('•' + clean_part)
                            result[field] = '\n'.join(formatted_parts)
                
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
            # Check if AI parsing is available
            if not self.client:
                print("⚠️  AI parsing not available (no API key). Using manual parsing fallback.")
                return {
                    "about_company": None,
                    "about_job": None,
                    "responsibilities": None,
                    "qualifications": None,
                    "benefits": None,
                    "salary_range": None,
                    "work_environment": None
                }
            
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
