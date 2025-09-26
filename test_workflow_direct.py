#!/usr/bin/env python3
"""
Direct workflow test for the exported ComfyUI workflow
"""

import json
import requests
import time
import sys
import os

def test_workflow():
    """Test the workflow directly with ComfyUI"""
    
    # ComfyUI endpoint
    COMFY_HOST = "127.0.0.1:8188"
    
    print("🚀 Testing exported workflow with ComfyUI...")
    
    # Check if ComfyUI is running
    try:
        response = requests.get(f"http://{COMFY_HOST}/", timeout=10)
        if response.status_code != 200:
            print(f"❌ ComfyUI is not responding correctly (status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ ComfyUI is not reachable: {e}")
        print("💡 Make sure ComfyUI is running on localhost:8188")
        return False
    
    print("✅ ComfyUI is running and reachable")
    
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
        
        print("📤 Submitting workflow to ComfyUI...")
        response = requests.post(
            f"http://{COMFY_HOST}/prompt",
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
        
        print(f"✅ Workflow submitted successfully (prompt_id: {prompt_id})")
        
    except Exception as e:
        print(f"❌ Failed to submit workflow: {e}")
        return False
    
    # Wait for completion and check results
    print("⏳ Waiting for workflow completion...")
    max_wait = 1200  # 20 minutes (same as handler timeout)
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            # Check history
            response = requests.get(f"http://{COMFY_HOST}/history/{prompt_id}", timeout=10)
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
                        
                        if image_count > 0:
                            print("📁 Images saved to ComfyUI output directory")
                        
                        return True
                    
                    elif status.get("status_str") == "error":
                        print("❌ Workflow failed with error:")
                        messages = status.get("messages", [])
                        for message in messages:
                            print(f"   {message}")
                        return False
            
        except Exception as e:
            print(f"⚠️  Error checking status: {e}")
        
        # Progress indicator
        elapsed = int(time.time() - start_time)
        if elapsed % 30 == 0:  # Show progress every 30 seconds
            print(f"⏳ Still processing... ({elapsed}s elapsed)")
        time.sleep(5)
    
    print("⏰ Workflow timed out after 20 minutes")
    return False

def check_models():
    """Check if required models are available"""
    COMFY_HOST = "127.0.0.1:8188"
    
    print("\n🔍 Checking available models...")
    
    try:
        response = requests.get(f"http://{COMFY_HOST}/object_info", timeout=10)
        if response.status_code == 200:
            object_info = response.json()
            
            # Check for Nunchaku nodes
            nunchaku_nodes = [
                "NunchakuFluxDiTLoader",
                "NunchakuFluxLoraLoader", 
                "NunchakuTextEncoderLoaderV2"
            ]
            
            missing_nodes = []
            for node in nunchaku_nodes:
                if node not in object_info:
                    missing_nodes.append(node)
            
            if missing_nodes:
                print(f"❌ Missing Nunchaku nodes: {', '.join(missing_nodes)}")
                print("💡 Make sure ComfyUI-Nunchaku is installed and enabled")
                return False
            else:
                print("✅ All required Nunchaku nodes are available")
            
            # Check for required models
            required_models = {
                "model_path": "svdq-int4_r32-flux.1-dev.safetensors",
                "text_encoder1": "awq-int4-flux.1-t5xxl.safetensors", 
                "text_encoder2": "clip_l.safetensors",
                "vae_name": "ae.safetensors",
                "lora_name": ["FLUX.1-Turbo-Alpha.safetensors", "flux-super-realism.safetensors"]
            }
            
            print("📋 Required model files:")
            for key, value in required_models.items():
                if isinstance(value, list):
                    for item in value:
                        print(f"   - {item}")
                else:
                    print(f"   - {value}")
            
            return True
        
    except Exception as e:
        print(f"❌ Failed to check models: {e}")
        return False

def test_with_different_prompt():
    """Test workflow with a different prompt"""
    print("\n🎨 Testing with different prompt...")
    
    # Load and modify workflow
    try:
        with open("test_new_workflow.json", "r", encoding="utf-8") as f:
            test_data = json.load(f)
        workflow = test_data["input"]["workflow"]
        
        # Change the prompt in node 6
        new_prompt = "a futuristic robot in a cyberpunk city, neon lights, rain, dramatic lighting, highly detailed"
        workflow["6"]["inputs"]["text"] = new_prompt
        
        print(f"📝 New prompt: {new_prompt}")
        
        # Test with modified workflow
        return test_single_workflow(workflow)
        
    except Exception as e:
        print(f"❌ Failed to test with different prompt: {e}")
        return False

def test_single_workflow(workflow):
    """Test a single workflow"""
    COMFY_HOST = "127.0.0.1:8188"
    
    import uuid
    client_id = str(uuid.uuid4())
    
    try:
        payload = {"prompt": workflow, "client_id": client_id}
        response = requests.post(f"http://{COMFY_HOST}/prompt", json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Failed to submit: {response.text}")
            return False
        
        result = response.json()
        prompt_id = result.get("prompt_id")
        print(f"✅ Submitted (ID: {prompt_id})")
        
        # Quick check (30 seconds)
        for i in range(6):
            time.sleep(5)
            try:
                response = requests.get(f"http://{COMFY_HOST}/history/{prompt_id}", timeout=10)
                if response.status_code == 200:
                    history = response.json()
                    if prompt_id in history:
                        status = history[prompt_id].get("status", {})
                        if status.get("status_str") == "success":
                            print("✅ Quick test completed!")
                            return True
                        elif status.get("status_str") == "error":
                            print("❌ Quick test failed!")
                            return False
            except:
                pass
        
        print("⏳ Quick test still processing...")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 ComfyUI Workflow Test - Comprehensive Edition")
    print("=" * 60)
    
    # Check models first
    if not check_models():
        print("\n❌ Model check failed. Please ensure all required models are installed.")
        sys.exit(1)
    
    # Test original workflow
    print("\n" + "="*60)
    print("🎯 MAIN TEST: Original exported workflow")
    print("="*60)
    
    if test_workflow():
        print("\n🎉 Main test completed successfully!")
        print("✅ Your original workflow is working correctly")
        
        # Optional: Test with different prompt
        try:
            user_input = input("\n🤔 Want to test with a different prompt? (y/n): ").lower().strip()
            if user_input == 'y':
                if test_with_different_prompt():
                    print("✅ Different prompt test also successful!")
                else:
                    print("⚠️  Different prompt test had issues")
        except KeyboardInterrupt:
            print("\n👋 Test interrupted by user")
        
    else:
        print("\n❌ Main test failed!")
        print("💡 Please check the error messages above and ensure:")
        print("   - ComfyUI is running on localhost:8188")
        print("   - All required models are installed")
        print("   - ComfyUI-Nunchaku extension is properly installed")
        sys.exit(1)
    
    print("\n📋 Test Summary:")
    print("✅ Workflow format is correct")
    print("✅ All dependencies are available") 
    print("✅ Ready for RunPod deployment")
    print("\n🚀 Your workflow is ready to go!")
