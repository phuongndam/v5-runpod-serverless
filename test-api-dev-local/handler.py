import json
import base64
import os
import sys
from typing import Dict, Any, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComfyUIHandler:
    def __init__(self, workflow_path: str = "workflow-data/text2image-nunchaku-flux.1-dev.json"):
        """
        Initialize the ComfyUI handler with workflow template
        
        Args:
            workflow_path: Path to the workflow JSON file
        """
        self.workflow_path = workflow_path
        self.workflow_template = self._load_workflow_template()
        
    def _load_workflow_template(self) -> Dict[str, Any]:
        """Load the workflow template from JSON file"""
        try:
            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Workflow file not found: {self.workflow_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in workflow file: {e}")
            raise
    
    def _update_workflow_parameters(self, prompt: str, width: int, height: int) -> Dict[str, Any]:
        """
        Update workflow parameters based on input
        
        Args:
            prompt: Text prompt for image generation
            width: Image width
            height: Image height
            
        Returns:
            Updated workflow dictionary
        """
        # Create a deep copy of the workflow template
        workflow = json.loads(json.dumps(self.workflow_template))
        
        # Find and update the prompt node (CLIPTextEncode - node id 6)
        for node in workflow.get('nodes', []):
            if node.get('id') == 6 and node.get('type') == 'CLIPTextEncode':
                node['widgets_values'][0] = prompt
                logger.info(f"Updated prompt: {prompt}")
                break
        
        # Find and update width node (PrimitiveNode - node id 34)
        for node in workflow.get('nodes', []):
            if node.get('id') == 34 and node.get('type') == 'PrimitiveNode' and node.get('title') == 'width':
                node['widgets_values'][0] = width
                logger.info(f"Updated width: {width}")
                break
        
        # Find and update height node (PrimitiveNode - node id 35)
        for node in workflow.get('nodes', []):
            if node.get('id') == 35 and node.get('type') == 'PrimitiveNode' and node.get('title') == 'height':
                node['widgets_values'][0] = height
                logger.info(f"Updated height: {height}")
                break
        
        # Update EmptySD3LatentImage node (node id 27) with new dimensions
        for node in workflow.get('nodes', []):
            if node.get('id') == 27 and node.get('type') == 'EmptySD3LatentImage':
                node['widgets_values'][0] = width
                node['widgets_values'][1] = height
                logger.info(f"Updated EmptySD3LatentImage: {width}x{height}")
                break
        
        # Update ModelSamplingFlux node (node id 30) with new dimensions
        for node in workflow.get('nodes', []):
            if node.get('id') == 30 and node.get('type') == 'ModelSamplingFlux':
                node['widgets_values'][2] = width  # width parameter
                node['widgets_values'][3] = height  # height parameter
                logger.info(f"Updated ModelSamplingFlux: {width}x{height}")
                break
        
        return workflow
    
    def validate_input(self, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input parameters
        
        Args:
            input_data: Input data dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ['prompt', 'width', 'height']
        
        for field in required_fields:
            if field not in input_data:
                return False, f"Missing required field: {field}"
        
        # Validate prompt
        if not isinstance(input_data['prompt'], str) or len(input_data['prompt'].strip()) == 0:
            return False, "Prompt must be a non-empty string"
        
        # Validate dimensions
        try:
            width = int(input_data['width'])
            height = int(input_data['height'])
            
            if width <= 0 or height <= 0:
                return False, "Width and height must be positive integers"
            
            if width > 2048 or height > 2048:
                return False, "Width and height must not exceed 2048 pixels"
                
        except (ValueError, TypeError):
            return False, "Width and height must be valid integers"
        
        return True, None
    
    def handler(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main handler function for RunPod serverless
        
        Args:
            event: Event data from RunPod
            
        Returns:
            Response dictionary
        """
        try:
            logger.info("Received event: %s", json.dumps(event, indent=2))
            
            # Extract input data
            input_data = event.get('input', {})
            
            # Validate input
            is_valid, error_msg = self.validate_input(input_data)
            if not is_valid:
                return {
                    "error": error_msg,
                    "status": "error"
                }
            
            # Extract parameters
            prompt = input_data['prompt'].strip()
            width = int(input_data['width'])
            height = int(input_data['height'])
            
            logger.info(f"Processing request - Prompt: '{prompt}', Size: {width}x{height}")
            
            # Update workflow with new parameters
            updated_workflow = self._update_workflow_parameters(prompt, width, height)
            
            # In a real implementation, you would:
            # 1. Send the workflow to ComfyUI API
            # 2. Wait for execution to complete
            # 3. Retrieve the generated image
            # 4. Return the image data
            
            # For now, we'll return the updated workflow as a simulation
            return {
                "status": "success",
                "message": "Workflow updated successfully",
                "workflow": updated_workflow,
                "parameters": {
                    "prompt": prompt,
                    "width": width,
                    "height": height
                }
            }
            
        except Exception as e:
            logger.error(f"Error in handler: {str(e)}", exc_info=True)
            return {
                "error": f"Internal server error: {str(e)}",
                "status": "error"
            }

# Global handler instance
handler_instance = ComfyUIHandler()

def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point for RunPod serverless function
    """
    return handler_instance.handler(event)

# For testing purposes
if __name__ == "__main__":
    # Test the handler with sample data
    test_event = {
        "input": {
            "prompt": "a beautiful landscape with mountains and lake, sunset, photorealistic",
            "width": 1024,
            "height": 768
        }
    }
    
    result = handler(test_event)
    print("Test result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
