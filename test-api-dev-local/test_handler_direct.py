#!/usr/bin/env python3
"""
Direct test script for ComfyUI Handler without API server
"""

import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handler import handler

def test_handler_direct():
    """Test handler directly with various inputs"""
    print("🧪 Testing ComfyUI Handler Directly")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Basic landscape generation",
            "input": {
                "prompt": "a beautiful landscape with mountains and lake, sunset, photorealistic",
                "width": 1024,
                "height": 768
            }
        },
        {
            "name": "Portrait mode (original workflow size)",
            "input": {
                "prompt": "magazine cover photo of a black supermodel, full body shot, low angle view from her feet, wide-angle lens, watching the sunset, hyperrealistic, vogue style",
                "width": 832,
                "height": 1280
            }
        },
        {
            "name": "Square format",
            "input": {
                "prompt": "a cute cat sitting on a windowsill, soft lighting, detailed fur texture",
                "width": 512,
                "height": 512
            }
        },
        {
            "name": "High resolution",
            "input": {
                "prompt": "a detailed architectural drawing of a modern building, clean lines, minimalist design",
                "width": 1920,
                "height": 1080
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print("-" * 30)
        
        try:
            # Create event in RunPod format
            event = {"input": test_case["input"]}
            
            print(f"📝 Input prompt: {test_case['input']['prompt'][:60]}...")
            print(f"📐 Dimensions: {test_case['input']['width']}x{test_case['input']['height']}")
            
            # Call handler
            result = handler(event)
            
            # Check result
            if result.get("status") == "success":
                print("✅ Handler executed successfully")
                
                # Verify parameters were updated correctly
                if "parameters" in result:
                    params = result["parameters"]
                    print(f"📊 Updated parameters:")
                    print(f"   Prompt: {params['prompt'][:60]}...")
                    print(f"   Width: {params['width']}")
                    print(f"   Height: {params['height']}")
                
                # Check if workflow was returned
                if "workflow" in result:
                    workflow = result["workflow"]
                    print(f"📋 Workflow contains {len(workflow.get('nodes', []))} nodes")
                    
                    # Verify specific nodes were updated
                    updated_nodes = []
                    for node in workflow.get('nodes', []):
                        if node.get('id') == 6 and node.get('type') == 'CLIPTextEncode':
                            updated_nodes.append(f"CLIPTextEncode: '{node['widgets_values'][0][:30]}...'")
                        elif node.get('id') == 34 and node.get('title') == 'width':
                            updated_nodes.append(f"Width: {node['widgets_values'][0]}")
                        elif node.get('id') == 35 and node.get('title') == 'height':
                            updated_nodes.append(f"Height: {node['widgets_values'][0]}")
                    
                    if updated_nodes:
                        print(f"🔧 Updated nodes: {', '.join(updated_nodes)}")
                
            else:
                print(f"❌ Handler failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Test error: {str(e)}")
            import traceback
            traceback.print_exc()

def test_error_handling():
    """Test error handling"""
    print(f"\n🚨 Testing Error Handling")
    print("=" * 50)
    
    error_cases = [
        {
            "name": "Missing prompt",
            "input": {"width": 1024, "height": 768}
        },
        {
            "name": "Missing width",
            "input": {"prompt": "test prompt", "height": 768}
        },
        {
            "name": "Missing height",
            "input": {"prompt": "test prompt", "width": 1024}
        },
        {
            "name": "Empty prompt",
            "input": {"prompt": "", "width": 1024, "height": 768}
        },
        {
            "name": "Invalid width (negative)",
            "input": {"prompt": "test", "width": -100, "height": 768}
        },
        {
            "name": "Invalid height (zero)",
            "input": {"prompt": "test", "width": 1024, "height": 0}
        },
        {
            "name": "Oversized dimensions",
            "input": {"prompt": "test", "width": 3000, "height": 2000}
        },
        {
            "name": "Invalid data types",
            "input": {"prompt": "test", "width": "not_a_number", "height": 768}
        }
    ]
    
    for i, test_case in enumerate(error_cases, 1):
        print(f"\n🔍 Error Test {i}: {test_case['name']}")
        print("-" * 30)
        
        try:
            event = {"input": test_case["input"]}
            result = handler(event)
            
            if result.get("status") == "error":
                print(f"✅ Correctly caught error: {result.get('error')}")
            else:
                print(f"❌ Should have failed but succeeded: {result}")
                
        except Exception as e:
            print(f"⚠️  Exception caught: {str(e)}")

def test_workflow_validation():
    """Test workflow structure validation"""
    print(f"\n🔍 Testing Workflow Validation")
    print("=" * 50)
    
    try:
        # Test with valid input
        event = {
            "input": {
                "prompt": "test prompt for validation",
                "width": 1024,
                "height": 768
            }
        }
        
        result = handler(event)
        
        if result.get("status") == "success" and "workflow" in result:
            workflow = result["workflow"]
            
            # Check required structure
            required_keys = ["id", "revision", "nodes", "links"]
            missing_keys = [key for key in required_keys if key not in workflow]
            
            if missing_keys:
                print(f"❌ Missing workflow keys: {missing_keys}")
            else:
                print("✅ Workflow has required structure")
            
            # Check node counts
            node_count = len(workflow.get("nodes", []))
            link_count = len(workflow.get("links", []))
            print(f"📊 Workflow stats: {node_count} nodes, {link_count} links")
            
            # Check specific nodes exist
            node_types = [node.get("type") for node in workflow.get("nodes", [])]
            expected_types = ["CLIPTextEncode", "PrimitiveNode", "EmptySD3LatentImage", "ModelSamplingFlux"]
            found_types = [t for t in expected_types if t in node_types]
            print(f"🔧 Found node types: {found_types}")
            
        else:
            print(f"❌ Failed to generate workflow: {result}")
            
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")

def main():
    """Run all direct tests"""
    print("🚀 Starting Direct Handler Tests")
    print("=" * 50)
    
    test_handler_direct()
    test_error_handling()
    test_workflow_validation()
    
    print("\n" + "=" * 50)
    print("✅ All direct tests completed!")

if __name__ == "__main__":
    main()
