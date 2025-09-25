#!/usr/bin/env python3
"""
Test script cho ComfyUI Serverless Handler
Test trực tiếp handler mà không cần FastAPI server
"""

import asyncio
import json
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from test_serverless_handler import (
    handler_sync, 
    handler_async, 
    load_workflow_template,
    test_handler_sync_with_workflow,
    test_handler_with_workflow
)

async def test_async_handler():
    """Test async handler"""
    print("🔄 Testing Async Handler...")
    
    # Load workflow template
    workflow_template = load_workflow_template()
    if not workflow_template:
        print("❌ Không thể load workflow template")
        return False
    
    # Test data
    input_data = {
        'text': 'magazine cover photo of a black supermodel, full body shot, low angle view from her feet, wide-angle lens, watching the sunset, hyperrealistic, vogue style',
        'seed': 12345
    }
    
    try:
        result = await test_handler_with_workflow(workflow_template, input_data)
        
        print("📊 Async Handler Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get('success'):
            print("✅ Async Handler Test thành công!")
            return True
        else:
            print("❌ Async Handler Test thất bại!")
            return False
            
    except Exception as e:
        print(f"❌ Async Handler Test error: {e}")
        return False

def test_sync_handler():
    """Test sync handler"""
    print("🔄 Testing Sync Handler...")
    
    # Load workflow template
    workflow_template = load_workflow_template()
    if not workflow_template:
        print("❌ Không thể load workflow template")
        return False
    
    # Test data
    input_data = {
        'text': 'a beautiful landscape with mountains and lake, sunset, photorealistic',
        'seed': 54321
    }
    
    try:
        result = test_handler_sync_with_workflow(workflow_template, input_data)
        
        print("📊 Sync Handler Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get('success'):
            print("✅ Sync Handler Test thành công!")
            return True
        else:
            print("❌ Sync Handler Test thất bại!")
            return False
            
    except Exception as e:
        print(f"❌ Sync Handler Test error: {e}")
        return False

async def test_direct_handler():
    """Test handler trực tiếp với job input"""
    print("🔄 Testing Direct Handler...")
    
    # Load workflow template
    workflow_template = load_workflow_template()
    if not workflow_template:
        print("❌ Không thể load workflow template")
        return False
    
    # Job input giống RunPod
    job_input = {
        'workflow': workflow_template,
        'input': {
            'text': 'test direct handler with runpod-like structure',
            'seed': 99999
        }
    }
    
    try:
        # Test async
        print("  📝 Testing async handler...")
        async_result = await handler_async(job_input)
        print(f"  ✅ Async result: {async_result.get('success', False)}")
        
        # Test sync
        print("  📝 Testing sync handler...")
        sync_result = handler_sync(job_input)
        print(f"  ✅ Sync result: {sync_result.get('success', False)}")
        
        print("📊 Direct Handler Results:")
        print("Async:", json.dumps(async_result, indent=2, ensure_ascii=False))
        print("Sync:", json.dumps(sync_result, indent=2, ensure_ascii=False))
        
        return async_result.get('success', False) and sync_result.get('success', False)
        
    except Exception as e:
        print(f"❌ Direct Handler Test error: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 ComfyUI Serverless Handler Test")
    print("=" * 50)
    
    # Test 1: Async Handler
    print("\n1️⃣ Testing Async Handler")
    async_success = await test_async_handler()
    
    # Test 2: Sync Handler
    print("\n2️⃣ Testing Sync Handler")
    sync_success = test_sync_handler()
    
    # Test 3: Direct Handler
    print("\n3️⃣ Testing Direct Handler")
    direct_success = await test_direct_handler()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"  Async Handler: {'✅ PASS' if async_success else '❌ FAIL'}")
    print(f"  Sync Handler:  {'✅ PASS' if sync_success else '❌ FAIL'}")
    print(f"  Direct Handler: {'✅ PASS' if direct_success else '❌ FAIL'}")
    
    overall_success = async_success and sync_success and direct_success
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    return overall_success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(1)
