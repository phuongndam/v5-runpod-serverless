"""
RunPod Serverless Handler for ComfyUI
Xử lý các request từ RunPod và tích hợp với ComfyUI API
"""

import os
import sys
import json
import asyncio
import logging
import traceback
from typing import Dict, Any, Optional
import aiohttp
import runpod
from PIL import Image
import base64
import io

# Thêm ComfyUI vào Python path
sys.path.append('/workspace/ComfyUI')

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComfyUIServerlessHandler:
    """Handler chính để xử lý ComfyUI requests trong môi trường serverless"""
    
    def __init__(self):
        self.comfyui_url = "http://localhost:8188"
        self.session = None
        self.initialized = False
        
    async def initialize(self):
        """Khởi tạo ComfyUI server nếu chưa chạy"""
        if self.initialized:
            return
            
        try:
            # Tạo aiohttp session
            self.session = aiohttp.ClientSession()
            
            # Kiểm tra ComfyUI server có đang chạy không
            await self._check_comfyui_health()
            
            self.initialized = True
            logger.info("ComfyUI Serverless Handler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ComfyUI handler: {e}")
            raise
    
    async def _check_comfyui_health(self):
        """Kiểm tra ComfyUI server có hoạt động không"""
        try:
            async with self.session.get(f"{self.comfyui_url}/system_stats") as response:
                if response.status == 200:
                    logger.info("ComfyUI server is running")
                    return True
                else:
                    raise Exception(f"ComfyUI server returned status {response.status}")
        except Exception as e:
            logger.error(f"ComfyUI server health check failed: {e}")
            raise
    
    async def process_workflow(self, workflow_data: Dict[str, Any], input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Xử lý workflow ComfyUI
        
        Args:
            workflow_data: Dữ liệu workflow JSON từ ComfyUI
            input_data: Dữ liệu input bổ sung (text prompts, images, etc.)
            
        Returns:
            Kết quả xử lý workflow
        """
        try:
            # Validate workflow
            if not self._validate_workflow(workflow_data):
                raise ValueError("Invalid workflow data")
            
            # Inject input data vào workflow nếu có
            if input_data:
                workflow_data = self._inject_input_data(workflow_data, input_data)
            
            # Submit workflow đến ComfyUI
            prompt_id = await self._submit_workflow(workflow_data)
            
            # Chờ kết quả
            result = await self._wait_for_completion(prompt_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing workflow: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _validate_workflow(self, workflow_data: Dict[str, Any]) -> bool:
        """Validate workflow data structure"""
        required_fields = ['nodes', 'links']
        return all(field in workflow_data for field in required_fields)
    
    def _inject_input_data(self, workflow_data: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject input data vào workflow
        Ví dụ: thay thế text prompts, load images từ base64, etc.
        """
        try:
            # Tìm các node cần inject data
            for node in workflow_data.get('nodes', []):
                node_type = node.get('type', '')
                
                # Inject text prompts
                if node_type == 'CLIPTextEncode' and 'text' in input_data:
                    if 'widgets_values' in node:
                        node['widgets_values'][0] = input_data['text']
                
                # Inject images từ base64
                elif node_type == 'LoadImage' and 'image_base64' in input_data:
                    # Tạo file tạm thời từ base64
                    image_data = base64.b64decode(input_data['image_base64'])
                    temp_filename = f"temp_input_{hash(input_data['image_base64']) % 10000}.png"
                    temp_path = f"/workspace/ComfyUI/input/{temp_filename}"
                    
                    # Lưu image
                    with open(temp_path, 'wb') as f:
                        f.write(image_data)
                    
                    # Cập nhật workflow để load image này
                    if 'widgets_values' in node:
                        node['widgets_values'][0] = temp_filename
                
                # Inject seed nếu có
                elif node_type == 'KSampler' and 'seed' in input_data:
                    if 'widgets_values' in node:
                        node['widgets_values'][0] = input_data['seed']
            
            return workflow_data
            
        except Exception as e:
            logger.error(f"Error injecting input data: {e}")
            return workflow_data
    
    async def _submit_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Submit workflow đến ComfyUI API"""
        try:
            payload = {
                "prompt": workflow_data,
                "client_id": "runpod-serverless"
            }
            
            async with self.session.post(
                f"{self.comfyui_url}/prompt",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    prompt_id = result.get('prompt_id')
                    logger.info(f"Workflow submitted with prompt_id: {prompt_id}")
                    return prompt_id
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to submit workflow: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error submitting workflow: {e}")
            raise
    
    async def _wait_for_completion(self, prompt_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Chờ workflow hoàn thành và lấy kết quả"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Kiểm tra queue status
                async with self.session.get(f"{self.comfyui_url}/queue") as response:
                    if response.status == 200:
                        queue_data = await response.json()
                        
                        # Kiểm tra xem prompt đã hoàn thành chưa
                        running = queue_data.get('queue_running', [])
                        if not any(item[1] == prompt_id for item in running):
                            # Prompt đã hoàn thành, lấy history
                            return await self._get_workflow_result(prompt_id)
                
                # Kiểm tra timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise TimeoutError(f"Workflow timeout after {timeout} seconds")
                
                # Chờ 1 giây trước khi kiểm tra lại
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error waiting for completion: {e}")
            raise
    
    async def _get_workflow_result(self, prompt_id: str) -> Dict[str, Any]:
        """Lấy kết quả workflow từ history"""
        try:
            async with self.session.get(f"{self.comfyui_url}/history/{prompt_id}") as response:
                if response.status == 200:
                    history_data = await response.json()
                    
                    if prompt_id in history_data:
                        prompt_data = history_data[prompt_id]
                        outputs = prompt_data.get('outputs', {})
                        
                        # Tìm các output images
                        result = {
                            'prompt_id': prompt_id,
                            'status': 'completed',
                            'outputs': {}
                        }
                        
                        for node_id, node_output in outputs.items():
                            if 'images' in node_output:
                                images = []
                                for img_info in node_output['images']:
                                    # Lấy image data
                                    image_url = f"{self.comfyui_url}/view?filename={img_info['filename']}&type=output"
                                    async with self.session.get(image_url) as img_response:
                                        if img_response.status == 200:
                                            image_data = await img_response.read()
                                            # Convert to base64
                                            image_base64 = base64.b64encode(image_data).decode('utf-8')
                                            images.append({
                                                'filename': img_info['filename'],
                                                'base64': image_base64,
                                                'type': img_info.get('type', 'output')
                                            })
                                
                                result['outputs'][node_id] = {
                                    'images': images
                                }
                        
                        return result
                    else:
                        raise Exception("Prompt not found in history")
                else:
                    raise Exception(f"Failed to get history: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error getting workflow result: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

# Global handler instance
handler = ComfyUIServerlessHandler()

async def handler_async(job_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler function cho RunPod serverless
    
    Args:
        job_input: Input data từ RunPod
        
    Returns:
        Kết quả xử lý
    """
    try:
        # Initialize handler nếu chưa
        if not handler.initialized:
            await handler.initialize()
        
        # Extract input data
        workflow_data = job_input.get('workflow')
        input_data = job_input.get('input', {})
        
        if not workflow_data:
            raise ValueError("No workflow data provided")
        
        # Process workflow
        result = await handler.process_workflow(workflow_data, input_data)
        
        return {
            'success': True,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"Handler error: {e}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

def handler_sync(job_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper cho RunPod
    """
    try:
        # Tạo event loop mới nếu chưa có
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Chạy async handler
        return loop.run_until_complete(handler_async(job_input))
        
    except Exception as e:
        logger.error(f"Sync handler error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

# RunPod handler
runpod.serverless.start({"handler": handler_sync})
