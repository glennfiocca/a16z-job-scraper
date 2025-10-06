#!/usr/bin/env python3
"""
Simple test to verify AI parser works with a sample job posting
"""

import os
import asyncio
from ai_parser import AIParser

async def test_ai_parser():
    """Test AI parser with a sample job posting"""
    
    print("🤖 AI PARSER SIMPLE TEST")
    print("=" * 40)
    
    # Check if API key is available
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment!")
        print("Available environment variables:")
        for key in sorted(os.environ.keys()):
            if 'OPENAI' in key or 'SECRET' in key or 'KEY' in key:
                print(f"  {key}: {'*' * 10}")
        print("\nTrying to set API key manually...")
        # You can manually set your API key here for testing
        # Uncomment the next two lines and add your actual API key:
        # api_key = "your-actual-api-key-here"
        # os.environ['OPENAI_API_KEY'] = api_key
        print("Please uncomment and add your API key in the test file, or set it as an environment variable")
        return
    
    print("✅ API key found!")
    
    try:
        # Initialize parser
        parser = AIParser()
        print("✅ AI parser initialized")
        
        # Test with sample job content
        sample_content = """
        Software Engineer - Full Stack
        
        Company: TechCorp Inc.
        Location: San Francisco, CA (Remote OK)
        
        About the Role:
        We're looking for a talented Software Engineer to join our team. You'll work on building scalable web applications and contribute to our growing platform.
        
        What You'll Do:
        - Build and maintain web applications
        - Collaborate with cross-functional teams
        - Write clean, maintainable code
        - Participate in code reviews
        
        Requirements:
        - 3+ years of software development experience
        - Proficiency in JavaScript, Python, and React
        - Experience with databases and APIs
        - Strong problem-solving skills
        
        Benefits:
        - Competitive salary ($120k-150k)
        - Health, dental, and vision insurance
        - 401k matching
        - Flexible work arrangements
        - Professional development budget
        """
        
        print("\n🔍 Testing with sample job content...")
        
        result = await parser.parse_greenhouse_job(sample_content, "https://example.com/job")
        
        print("\n📊 RESULTS:")
        print("-" * 20)
        for key, value in result.items():
            if value:
                print(f"{key}: {value}")
            else:
                print(f"{key}: (not extracted)")
        
        print("\n✅ Test completed successfully!")
        print("💡 If this looks good, we can integrate it into your main system.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure OPENAI_API_KEY is set correctly")
        print("2. Check your OpenAI account has credits")
        print("3. Verify the API key has proper permissions")

if __name__ == "__main__":
    asyncio.run(test_ai_parser())
