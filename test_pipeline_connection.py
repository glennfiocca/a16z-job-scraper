#!/usr/bin/env python3
"""
Test Pipeline API connection and endpoints
"""

import requests
import json
import os

# Configuration
PIPELINE_API_URL = "https://atpipeline.com"
PIPELINE_API_KEY = "sPqH575yX54u1x72G2sLoUhc18nsqUJcqnMq3cYR"

def test_health_endpoint():
    """Test the health endpoint"""
    print("🧪 Testing Pipeline API health endpoint...")
    
    try:
        response = requests.get(
            f"{PIPELINE_API_URL}/api/health",
            headers={'X-API-Key': PIPELINE_API_KEY},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Health endpoint working!")
            return True
        else:
            print("❌ Health endpoint failed!")
            return False
            
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False

def test_webhook_endpoint():
    """Test the webhook endpoint"""
    print("\n🧪 Testing Pipeline API webhook endpoint...")
    
    test_job = {
        'title': 'Test Job',
        'company': 'Test Company',
        'aboutJob': 'This is a test job for API testing.',
        'salaryRange': '$50,000 - $70,000',
        'location': 'Test City, Test State',
        'qualifications': 'Test qualifications',
        'source': 'A16Z Jobs',
        'sourceUrl': 'https://example.com/test-job',
        'employmentType': 'full-time',
        'postedDate': '2024-01-01T00:00:00Z',
        'aboutCompany': 'Test company description',
        'alternateLocations': 'Remote'
    }
    
    try:
        response = requests.post(
            f"{PIPELINE_API_URL}/api/webhook/jobs",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': PIPELINE_API_KEY
            },
            json={
                'jobs': [test_job],
                'source': 'A16Z Scraper Test'
            },
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("✅ Webhook endpoint working!")
                print(f"   Result: {result}")
                return True
            except json.JSONDecodeError as e:
                print(f"❌ Webhook returned invalid JSON: {e}")
                return False
        else:
            print("❌ Webhook endpoint failed!")
            return False
            
    except Exception as e:
        print(f"❌ Webhook endpoint error: {e}")
        return False

def test_batch_endpoint():
    """Test the batch endpoint"""
    print("\n🧪 Testing Pipeline API batch endpoint...")
    
    test_jobs = [
        {
            'title': 'Test Job 1',
            'company': 'Test Company 1',
            'aboutJob': 'This is test job 1.',
            'salaryRange': '$50,000 - $70,000',
            'location': 'Test City 1, Test State',
            'qualifications': 'Test qualifications 1',
            'source': 'A16Z Jobs',
            'sourceUrl': 'https://example.com/test-job-1',
            'employmentType': 'full-time',
            'postedDate': '2024-01-01T00:00:00Z',
            'aboutCompany': 'Test company 1 description',
            'alternateLocations': 'Remote'
        },
        {
            'title': 'Test Job 2',
            'company': 'Test Company 2',
            'aboutJob': 'This is test job 2.',
            'salaryRange': '$60,000 - $80,000',
            'location': 'Test City 2, Test State',
            'qualifications': 'Test qualifications 2',
            'source': 'A16Z Jobs',
            'sourceUrl': 'https://example.com/test-job-2',
            'employmentType': 'full-time',
            'postedDate': '2024-01-01T00:00:00Z',
            'aboutCompany': 'Test company 2 description',
            'alternateLocations': 'Remote'
        }
    ]
    
    try:
        response = requests.post(
            f"{PIPELINE_API_URL}/api/batch/jobs",
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': PIPELINE_API_KEY
            },
            json={
                'jobs': test_jobs,
                'source': 'A16Z Scraper Test'
            },
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("✅ Batch endpoint working!")
                print(f"   Result: {result}")
                return True
            except json.JSONDecodeError as e:
                print(f"❌ Batch returned invalid JSON: {e}")
                return False
        else:
            print("❌ Batch endpoint failed!")
            return False
            
    except Exception as e:
        print(f"❌ Batch endpoint error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Pipeline API Connection")
    print("=" * 50)
    print(f"API URL: {PIPELINE_API_URL}")
    print(f"API Key: {PIPELINE_API_KEY[:10]}...")
    print("=" * 50)
    
    # Test all endpoints
    health_ok = test_health_endpoint()
    webhook_ok = test_webhook_endpoint()
    batch_ok = test_batch_endpoint()
    
    print("\n📊 Test Results:")
    print(f"   Health Endpoint: {'✅' if health_ok else '❌'}")
    print(f"   Webhook Endpoint: {'✅' if webhook_ok else '❌'}")
    print(f"   Batch Endpoint: {'✅' if batch_ok else '❌'}")
    
    if health_ok and webhook_ok and batch_ok:
        print("\n🎉 All Pipeline API endpoints are working!")
        return True
    else:
        print("\n❌ Some Pipeline API endpoints are not working.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
