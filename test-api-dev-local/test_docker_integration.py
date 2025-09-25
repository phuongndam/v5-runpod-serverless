#!/usr/bin/env python3
"""
Test script for Docker integration
Tests the handler inside the Docker container
"""

import subprocess
import json
import time
import os
import sys

def run_docker_command(cmd, cwd=None):
    """Run a command inside the Docker container"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def test_docker_build():
    """Test if Docker image builds successfully"""
    print("🐳 Testing Docker build...")
    
    # Check if Dockerfile exists
    dockerfile_path = "../Dockerfile"
    if not os.path.exists(dockerfile_path):
        print(f"❌ Dockerfile not found at {dockerfile_path}")
        return False
    
    # Build Docker image
    print("   Building Docker image...")
    success, stdout, stderr = run_docker_command(
        "docker build -t comfyui-runpod-test -f ../Dockerfile ..",
        cwd="."
    )
    
    if success:
        print("✅ Docker image built successfully")
        return True
    else:
        print(f"❌ Docker build failed:")
        print(f"   stdout: {stdout}")
        print(f"   stderr: {stderr}")
        return False

def test_handler_in_container():
    """Test handler inside Docker container"""
    print("\n🧪 Testing handler in Docker container...")
    
    # Create test script content
    test_script = '''
import sys
import json
import os

# Add the handler to path
sys.path.append('/app')

try:
    from handler import handler
    
    # Test data
    test_event = {
        "input": {
            "prompt": "a beautiful landscape with mountains and lake, sunset, photorealistic",
            "width": 1024,
            "height": 768
        }
    }
    
    print("Testing handler...")
    result = handler(test_event)
    
    if result.get("status") == "success":
        print("✅ Handler test passed")
        print(f"Parameters: {result.get('parameters', {})}")
        print(f"Workflow nodes: {len(result.get('workflow', {}).get('nodes', []))}")
    else:
        print(f"❌ Handler test failed: {result.get('error')}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Handler test error: {str(e)}")
    sys.exit(1)
'''
    
    # Write test script to temporary file
    with open("test_container_handler.py", "w") as f:
        f.write(test_script)
    
    try:
        # Run test in container
        print("   Running handler test in container...")
        success, stdout, stderr = run_docker_command(
            "docker run --rm -v $(pwd):/test comfyui-runpod-test python /test/test_container_handler.py"
        )
        
        if success:
            print("✅ Handler works in Docker container")
            print(f"   Output: {stdout}")
            return True
        else:
            print(f"❌ Handler test failed in container:")
            print(f"   stdout: {stdout}")
            print(f"   stderr: {stderr}")
            return False
            
    finally:
        # Clean up test file
        if os.path.exists("test_container_handler.py"):
            os.remove("test_container_handler.py")

def test_workflow_file_access():
    """Test if workflow file is accessible in container"""
    print("\n📁 Testing workflow file access in container...")
    
    test_script = '''
import os
import json

workflow_path = "/app/workflow-data/text2image-nunchaku-flux.1-dev.json"

if os.path.exists(workflow_path):
    print("✅ Workflow file exists")
    try:
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        print(f"✅ Workflow loaded successfully - {len(workflow.get('nodes', []))} nodes")
    except Exception as e:
        print(f"❌ Failed to load workflow: {e}")
else:
    print(f"❌ Workflow file not found at {workflow_path}")
    print("Available files in /app:")
    for root, dirs, files in os.walk("/app"):
        for file in files:
            if file.endswith('.json'):
                print(f"  {os.path.join(root, file)}")
'''
    
    with open("test_workflow_access.py", "w") as f:
        f.write(test_script)
    
    try:
        success, stdout, stderr = run_docker_command(
            "docker run --rm -v $(pwd):/test comfyui-runpod-test python /test/test_workflow_access.py"
        )
        
        if success:
            print("✅ Workflow file access test passed")
            print(f"   Output: {stdout}")
            return True
        else:
            print(f"❌ Workflow file access test failed:")
            print(f"   stdout: {stdout}")
            print(f"   stderr: {stderr}")
            return False
            
    finally:
        if os.path.exists("test_workflow_access.py"):
            os.remove("test_workflow_access.py")

def test_api_server_in_container():
    """Test API server in container"""
    print("\n🌐 Testing API server in container...")
    
    # Create a simple test to start the API server
    test_script = '''
import sys
import os
import time
import threading
import requests
import json

# Add the handler to path
sys.path.append('/app')

def start_server():
    try:
        from runpod_mock_server import app
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")
    except Exception as e:
        print(f"Server error: {e}")

# Start server in background
server_thread = threading.Thread(target=start_server)
server_thread.daemon = True
server_thread.start()

# Wait for server to start
time.sleep(5)

# Test the server
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        print("✅ API server started successfully")
        
        # Test a simple request
        test_data = {
            "prompt": "test prompt",
            "width": 512,
            "height": 512
        }
        
        response = requests.post(
            "http://localhost:8000/runsync",
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ API request successful")
            result = response.json()
            print(f"Job ID: {result.get('id')}")
        else:
            print(f"❌ API request failed: {response.status_code}")
            
    else:
        print(f"❌ Health check failed: {response.status_code}")
        
except Exception as e:
    print(f"❌ API test error: {e}")
'''
    
    with open("test_api_container.py", "w") as f:
        f.write(test_script)
    
    try:
        print("   Starting API server in container...")
        success, stdout, stderr = run_docker_command(
            "docker run --rm -p 8000:8000 -v $(pwd):/test comfyui-runpod-test python /test/test_api_container.py",
            timeout=30
        )
        
        if success:
            print("✅ API server test passed")
            print(f"   Output: {stdout}")
            return True
        else:
            print(f"❌ API server test failed:")
            print(f"   stdout: {stdout}")
            print(f"   stderr: {stderr}")
            return False
            
    finally:
        if os.path.exists("test_api_container.py"):
            os.remove("test_api_container.py")

def main():
    """Run all Docker integration tests"""
    print("🚀 Starting Docker Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Docker Build", test_docker_build),
        ("Workflow File Access", test_workflow_file_access),
        ("Handler in Container", test_handler_in_container),
        ("API Server in Container", test_api_server_in_container)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 Test Summary:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All Docker integration tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
