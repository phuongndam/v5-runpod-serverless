#!/usr/bin/env python3
"""
Docker-aware workflow test for ComfyUI
Works both from host machine and inside container
"""

import json
import requests
import time
import sys
import os
import socket

def detect_environment():
    """Detect if we're running inside Docker or on host"""
    try:
        # Check if we're in a Docker container
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        return False

def get_comfyui_endpoints():
    """Get the appropriate ComfyUI endpoints based on environment"""
    is_docker = detect_environment()
    
    if is_docker:
        # Inside container - use internal network
        hosts = [
            "127.0.0.1:8188",  # Local in container
            "localhost:8188",   # Alternative local
        ]
    else:
        # On host machine - use exposed ports
        hosts = [
            "127.0.0.1:8188",   # Docker exposed port
            "localhost:8188",    # Alternative
        ]
    
    return hosts, is_docker

def test_connectivity():
    """Test connectivity to ComfyUI"""
    hosts, is_docker = get_comfyui_endpoints()
    
    print(f"🔍 Environment: {'Docker Container' if is_docker else 'Host Machine'}")
    print("🌐 Testing ComfyUI connectivity...")
    
    working_host = None
    for host in hosts:
        print(f"   Trying {host}...")
        try:
            response = requests.get(f"http://{host}/", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ Connected to ComfyUI at {host}")
                working_host = host
                break
        except Exception as e:
            print(f"   ❌ Failed to connect to {host}: {e}")
    
    if not working_host:
        print("\n❌ Could not connect to ComfyUI on any endpoint!")
        print("💡 Make sure:")
        if is_docker:
            print("   - ComfyUI is running in the container")
            print("   - ComfyUI is listening on 0.0.0.0:8188")
        else:
            print("   - Docker container is running")
            print("   - Ports 8188 and 8000 are properly exposed")
            print("   - Try: docker ps | grep 8188")
        return None
    
    return working_host

def test_docker_status():
    """Check Docker container status from host"""
    if detect_environment():
        print("🐳 Running inside Docker container")
        return True
    
    print("🖥️  Running on host machine")
    print("🔍 Checking Docker container status...")
    
    try:
        import subprocess
        # Check if docker command is available
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            output = result.stdout
            if '8188' in output:
                print("   ✅ Found Docker container with port 8188 exposed")
                # Extract container info
                lines = output.split('\n')
                for line in lines:
                    if '8188' in line:
                        print(f"   📦 Container: {line.split()[0][:12]}...")
                return True
            else:
                print("   ⚠️  No container found with port 8188 exposed")
                print("   💡 Try: docker-compose up -d")
        else:
            print("   ❌ Docker command failed")
    except subprocess.TimeoutExpired:
        print("   ⏰ Docker command timed out")
    except FileNotFoundError:
        print("   ❌ Docker command not found")
    except Exception as e:
        print(f"   ❌ Error checking Docker: {e}")
    
    return False

def test_workflow_with_host(comfy_host):
    """Test the workflow with specific ComfyUI host"""
    
    print(f"🚀 Testing workflow with ComfyUI at {comfy_host}...")
    
    # Load the workflow
    try:
        with open("test_new_workflow.json", "r", encoding="utf-8") as f:
            test_data = json.load(f)
        workflow = test_data["input"]["workflow"]
        print("✅ Workflow loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load workflow: {e}")
        return False
    
    # Generate unique client ID
    import uuid
    client_id = str(uuid.uuid4())
    
    # Submit workflow to ComfyUI
    try:
        payload = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        print("📤 Submitting workflow...")
        response = requests.post(
            f"http://{comfy_host}/prompt",
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to submit workflow (status: {response.status_code})")
            print(f"Response: {response.text}")
            return False
        
        result = response.json()
        prompt_id = result.get("prompt_id")
        if not prompt_id:
            print(f"❌ No prompt_id received: {result}")
            return False
        
        print(f"✅ Workflow submitted (ID: {prompt_id})")
        
    except Exception as e:
        print(f"❌ Failed to submit workflow: {e}")
        return False
    
    # Wait for completion
    print("⏳ Waiting for completion...")
    max_wait = 300  # 5 minutes for quick test
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"http://{comfy_host}/history/{prompt_id}", timeout=10)
            if response.status_code == 200:
                history = response.json()
                
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    status = prompt_history.get("status", {})
                    
                    if status.get("status_str") == "success":
                        print("✅ Workflow completed successfully!")
                        
                        # Check for generated images
                        outputs = prompt_history.get("outputs", {})
                        image_count = 0
                        
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                image_count += len(node_output["images"])
                        
                        print(f"🖼️  Generated {image_count} image(s)")
                        return True
                    
                    elif status.get("status_str") == "error":
                        print("❌ Workflow failed:")
                        messages = status.get("messages", [])
                        for message in messages:
                            print(f"   {message}")
                        return False
            
        except Exception as e:
            print(f"⚠️  Error checking status: {e}")
        
        # Progress indicator
        elapsed = int(time.time() - start_time)
        if elapsed > 0 and elapsed % 30 == 0:
            print(f"⏳ Still processing... ({elapsed}s)")
        time.sleep(5)
    
    print("⏰ Workflow timed out after 5 minutes")
    return False

def check_supervisor(comfy_host):
    """Check if supervisor is also available"""
    supervisor_host = comfy_host.replace('8188', '8000')
    
    print(f"\n🔍 Checking supervisor at {supervisor_host}...")
    try:
        response = requests.get(f"http://{supervisor_host}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Supervisor health: {health_data.get('status')}")
            return True
        else:
            print(f"⚠️  Supervisor responded with status: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Supervisor not reachable: {e}")
    
    return False

if __name__ == "__main__":
    print("🐳 Docker-Aware ComfyUI Workflow Test")
    print("=" * 50)
    
    # Test Docker status
    test_docker_status()
    
    # Test connectivity
    comfy_host = test_connectivity()
    if not comfy_host:
        sys.exit(1)
    
    # Check supervisor
    check_supervisor(comfy_host)
    
    # Test workflow
    print("\n" + "="*50)
    print("🎯 Testing Workflow")
    print("="*50)
    
    if test_workflow_with_host(comfy_host):
        print("\n🎉 Test completed successfully!")
        print("✅ Your workflow works correctly in this environment")
        print(f"✅ ComfyUI accessible at: {comfy_host}")
    else:
        print("\n❌ Test failed!")
        print("💡 Check the error messages above")
        sys.exit(1)
    
    print("\n📋 Environment Summary:")
    _, is_docker = get_comfyui_endpoints()
    if is_docker:
        print("🐳 Running inside Docker container")
        print("✅ Direct access to ComfyUI")
    else:
        print("🖥️  Running on host machine")
        print("✅ Accessing ComfyUI through exposed Docker ports")
    
    print("\n🚀 Ready for production!")
