"""
Test script cho RunPod handler
"""

import json
import asyncio
import sys
sys.path.append('.')

from rp_handler import handler_async

async def test_handler():
    """Test handler với workflow mẫu"""
    
    # Load workflow từ file
    with open('workflow/250922-render-screenshot-image-FLUX.json', 'r') as f:
        workflow_data = json.load(f)
    
    # Input data cho test
    input_data = {
        "text": "A beautiful landscape with mountains and lake, photorealistic, 8k",
        "seed": 12345
    }
    
    # Job input
    job_input = {
        "workflow": workflow_data,
        "input": input_data
    }
    
    print("Testing RunPod handler...")
    print(f"Workflow nodes: {len(workflow_data.get('nodes', []))}")
    print(f"Input text: {input_data['text']}")
    
    try:
        result = await handler_async(job_input)
        print(f"Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_handler())
