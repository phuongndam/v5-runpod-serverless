#!/usr/bin/env python3
"""
Quick test script to verify handler functionality
"""

import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_handler_quick():
    """Quick test of the handler"""
    print("🚀 Quick Handler Test")
    print("=" * 30)
    
    try:
        from handler import handler
        
        # Test case
        test_event = {
            "input": {
                "prompt": "a beautiful sunset over the ocean, photorealistic",
                "width": 1024,
                "height": 768
            }
        }
        
        print(f"📝 Testing with prompt: {test_event['input']['prompt']}")
        print(f"📐 Dimensions: {test_event['input']['width']}x{test_event['input']['height']}")
        
        # Call handler
        result = handler(test_event)
        
        # Check result
        if result.get("status") == "success":
            print("✅ Handler executed successfully!")
            
            # Show parameters
            if "parameters" in result:
                params = result["parameters"]
                print(f"📊 Updated parameters:")
                print(f"   Prompt: {params['prompt']}")
                print(f"   Width: {params['width']}")
                print(f"   Height: {params['height']}")
            
            # Show workflow info
            if "workflow" in result:
                workflow = result["workflow"]
                print(f"📋 Workflow info:")
                print(f"   Nodes: {len(workflow.get('nodes', []))}")
                print(f"   Links: {len(workflow.get('links', []))}")
                
                # Check if specific nodes were updated
                for node in workflow.get('nodes', []):
                    if node.get('id') == 6 and node.get('type') == 'CLIPTextEncode':
                        print(f"   ✅ CLIPTextEncode updated: '{node['widgets_values'][0][:50]}...'")
                    elif node.get('id') == 34 and node.get('title') == 'width':
                        print(f"   ✅ Width node updated: {node['widgets_values'][0]}")
                    elif node.get('id') == 35 and node.get('title') == 'height':
                        print(f"   ✅ Height node updated: {node['widgets_values'][0]}")
            
            print("\n🎉 Test completed successfully!")
            return True
            
        else:
            print(f"❌ Handler failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_handler_quick()
    sys.exit(0 if success else 1)
