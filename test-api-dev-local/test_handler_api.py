#!/usr/bin/env python3
"""
Test script for the Mock RunPod API and ComfyUI Handler
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_sync_generation():
    """Test synchronous image generation"""
    print("\n🖼️  Testing synchronous generation...")
    
    test_cases = [
        {
            "name": "Basic landscape",
            "data": {
                "prompt": "a beautiful landscape with mountains and lake, sunset, photorealistic",
                "width": 1024,
                "height": 768
            }
        },
        {
            "name": "Portrait mode",
            "data": {
                "prompt": "magazine cover photo of a black supermodel, full body shot, low angle view from her feet, wide-angle lens, watching the sunset, hyperrealistic, vogue style",
                "width": 832,
                "height": 1280
            }
        },
        {
            "name": "Square format",
            "data": {
                "prompt": "a cute cat sitting on a windowsill, soft lighting, detailed fur texture",
                "width": 512,
                "height": 512
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n   Testing: {test_case['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/runsync",
                json=test_case['data'],
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Success - Job ID: {result['id']}")
                print(f"   📊 Status: {result['status']}")
                
                # Check if workflow was updated correctly
                if 'output' in result and 'parameters' in result['output']:
                    params = result['output']['parameters']
                    print(f"   📝 Prompt: {params['prompt'][:50]}...")
                    print(f"   📐 Size: {params['width']}x{params['height']}")
                
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_async_generation():
    """Test asynchronous image generation"""
    print("\n⏳ Testing asynchronous generation...")
    
    # Submit job
    job_data = {
        "prompt": "a futuristic cityscape at night, neon lights, cyberpunk style, highly detailed",
        "width": 1024,
        "height": 1024
    }
    
    try:
        print("   Submitting async job...")
        response = requests.post(
            f"{BASE_URL}/run",
            json=job_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            job_id = result['id']
            print(f"   ✅ Job submitted - ID: {job_id}")
            
            # Poll for completion
            print("   ⏳ Polling for completion...")
            max_attempts = 10
            for attempt in range(max_attempts):
                time.sleep(1)
                
                status_response = requests.get(f"{BASE_URL}/status/{job_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"   📊 Status: {status['status']}")
                    
                    if status['status'] == 'COMPLETED':
                        print("   ✅ Job completed successfully!")
                        if status.get('result'):
                            print(f"   📝 Result keys: {list(status['result'].keys())}")
                        break
                    elif status['status'] == 'FAILED':
                        print(f"   ❌ Job failed: {status.get('error', 'Unknown error')}")
                        break
                else:
                    print(f"   ❌ Status check failed: {status_response.status_code}")
                    break
            else:
                print("   ⏰ Timeout waiting for job completion")
        else:
            print(f"   ❌ Job submission failed: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_error_handling():
    """Test error handling"""
    print("\n🚨 Testing error handling...")
    
    error_cases = [
        {
            "name": "Missing prompt",
            "data": {"width": 1024, "height": 768}
        },
        {
            "name": "Invalid dimensions",
            "data": {"prompt": "test", "width": -100, "height": 768}
        },
        {
            "name": "Empty prompt",
            "data": {"prompt": "", "width": 1024, "height": 768}
        },
        {
            "name": "Oversized dimensions",
            "data": {"prompt": "test", "width": 3000, "height": 2000}
        }
    ]
    
    for test_case in error_cases:
        print(f"\n   Testing: {test_case['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/runsync",
                json=test_case['data'],
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 400:
                print(f"   ✅ Correctly rejected - {response.json().get('detail', 'Unknown error')}")
            else:
                print(f"   ❌ Should have been rejected but got: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_job_management():
    """Test job management endpoints"""
    print("\n📋 Testing job management...")
    
    try:
        # List jobs
        response = requests.get(f"{BASE_URL}/jobs")
        if response.status_code == 200:
            jobs = response.json()
            print(f"   ✅ Listed {len(jobs['jobs'])} jobs")
            
            # If there are jobs, try to get status of the first one
            if jobs['jobs']:
                first_job_id = jobs['jobs'][0]['id']
                status_response = requests.get(f"{BASE_URL}/status/{first_job_id}")
                if status_response.status_code == 200:
                    print(f"   ✅ Retrieved status for job {first_job_id}")
                else:
                    print(f"   ❌ Failed to get job status: {status_response.status_code}")
        else:
            print(f"   ❌ Failed to list jobs: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    """Run all tests"""
    print("🚀 Starting Mock RunPod API Tests")
    print("=" * 50)
    
    # Check if server is running
    if not test_health_check():
        print("\n❌ Server is not running. Please start the server first:")
        print("   python runpod_mock_server.py")
        sys.exit(1)
    
    # Run tests
    test_sync_generation()
    test_async_generation()
    test_error_handling()
    test_job_management()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")

if __name__ == "__main__":
    main()
