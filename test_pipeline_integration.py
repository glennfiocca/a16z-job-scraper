#!/usr/bin/env python3
"""
Test script for Pipeline API integration
"""

import os
import sys
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the Pipeline functions
from main import send_job_to_pipeline, send_batch_to_pipeline, PIPELINE_API_URL, PIPELINE_API_KEY

# Set the API key for testing
os.environ['PIPELINE_API_KEY'] = 'sPqH575yX54u1x72G2sLoUhc18nsqUJcqnMq3cYR'

def test_single_job():
    """Test sending a single job to Pipeline"""
    print("🧪 Testing single job to Pipeline...")
    
    test_job = {
        'title': 'Test Software Engineer',
        'company': 'Test Company',
        'about_job': 'This is a test job description for testing the Pipeline integration.',
        'salary_range': '$80,000 - $120,000',
        'location': 'San Francisco, CA',
        'qualifications': 'Python, JavaScript, React',
        'source_url': 'https://example.com/test-job',
        'employment_type': 'full-time',
        'about_company': 'A test company for testing purposes',
        'alternate_locations': 'Remote, New York, NY'
    }
    
    success = send_job_to_pipeline(test_job)
    if success:
        print("✅ Single job test passed!")
    else:
        print("❌ Single job test failed!")
    return success

def test_batch_jobs():
    """Test sending multiple jobs to Pipeline"""
    print("🧪 Testing batch jobs to Pipeline...")
    
    test_jobs = [
        {
            'title': 'Test Frontend Developer',
            'company': 'Test Company A',
            'about_job': 'Frontend development role for testing.',
            'salary_range': '$70,000 - $100,000',
            'location': 'New York, NY',
            'qualifications': 'React, TypeScript, CSS',
            'source_url': 'https://example.com/test-job-1',
            'employment_type': 'full-time',
            'about_company': 'Test Company A description',
            'alternate_locations': 'Remote'
        },
        {
            'title': 'Test Backend Developer',
            'company': 'Test Company B',
            'about_job': 'Backend development role for testing.',
            'salary_range': '$90,000 - $130,000',
            'location': 'Seattle, WA',
            'qualifications': 'Python, Django, PostgreSQL',
            'source_url': 'https://example.com/test-job-2',
            'employment_type': 'full-time',
            'about_company': 'Test Company B description',
            'alternate_locations': 'Remote, Austin, TX'
        }
    ]
    
    success = send_batch_to_pipeline(test_jobs)
    if success:
        print("✅ Batch jobs test passed!")
    else:
        print("❌ Batch jobs test failed!")
    return success

def test_connection():
    """Test connection to Pipeline API"""
    print("🧪 Testing Pipeline API connection...")
    
    try:
        import requests
        response = requests.get(
            f"{PIPELINE_API_URL}/api/health",
            headers={'X-API-Key': PIPELINE_API_KEY},
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Pipeline API connection successful!")
            print(f"   API URL: {PIPELINE_API_URL}")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Pipeline API connection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Pipeline API connection error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Pipeline Integration Tests")
    print("=" * 50)
    
    # Test connection first
    if not test_connection():
        print("\n❌ Cannot connect to Pipeline API. Please check:")
        print("   1. Pipeline server is running")
        print("   2. PIPELINE_API_URL is correct")
        print("   3. PIPELINE_API_KEY is correct")
        return False
    
    print()
    
    # Test single job
    single_success = test_single_job()
    print()
    
    # Test batch jobs
    batch_success = test_batch_jobs()
    print()
    
    # Summary
    print("📊 Test Results:")
    print(f"   Connection: {'✅' if test_connection() else '❌'}")
    print(f"   Single Job: {'✅' if single_success else '❌'}")
    print(f"   Batch Jobs: {'✅' if batch_success else '❌'}")
    
    if single_success and batch_success:
        print("\n🎉 All tests passed! Pipeline integration is working!")
        return True
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
