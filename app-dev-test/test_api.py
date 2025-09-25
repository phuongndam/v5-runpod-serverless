#!/usr/bin/env python3
"""
Test script để kiểm tra API
"""

import requests
import json
import time

def test_api():
    """Test API server"""
    api_url = "http://localhost:8000"
    
    # Test health check
    print("Testing health check...")
    try:
        response = requests.get(f"{api_url}/health")
        print(f"Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return
    
    # Test generate image
    print("\nTesting image generation...")
    test_data = {
        "prompt": "a beautiful landscape with mountains and lake",
        "w": 1024,
        "h": 768
    }
    
    try:
        response = requests.post(
            f"{api_url}/generate",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Generate response: {response.status_code}")
        result = response.json()
        print(f"Result: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            print("✅ Image generation successful!")
        else:
            print("❌ Image generation failed!")
            
    except Exception as e:
        print(f"Generate request failed: {e}")

if __name__ == "__main__":
    print("Testing ComfyUI API...")
    print("Make sure the container is running with:")
    print("  docker-compose up")
    print()
    
    test_api()
