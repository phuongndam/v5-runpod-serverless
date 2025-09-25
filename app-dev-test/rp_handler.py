"""
Docker Worker Handler for ComfyUI
Xử lý các request từ API server và tích hợp với ComfyUI
"""

import os
import sys
import json
import asyncio
import logging
import traceback
import time
from typing import Dict, Any, Optional
import aiohttp
from PIL import Image
import base64
import io

# Thêm ComfyUI vào Python path
sys.path.append('/app/ComfyUI')

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComfyUIWorker:
    """Worker chính để xử lý ComfyUI requests"""
    
    def __init__(self):
        self.comfyui_url = "http://localhost:8188"
        self.session = None
        self.initialized = False
        
    async def initialize(self):
        """Khởi tạo worker"""
        if self.initialized:
            return
            
        try:
            # Tạo aiohttp session
            self.session = aiohttp.ClientSession()
            
            # Kiểm tra ComfyUI server có đang chạy không
            await self._check_comfyui_health()
            
            self.initialized = True
            logger.info("ComfyUI Worker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ComfyUI worker: {e}")
            raise
    
    async def _check_comfyui_health(self):
        """Kiểm tra ComfyUI server có hoạt động không"""
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                async with self.session.get(f"{self.comfyui_url}/system_stats") as response:
                    if response.status == 200:
                        logger.info("ComfyUI server is running")
                        return True
                    else:
                        logger.warning(f"ComfyUI server returned status {response.status}")
            except Exception as e:
                logger.warning(f"ComfyUI health check failed (attempt {retry_count + 1}): {e}")
            
            retry_count += 1
            await asyncio.sleep(2)
        
        raise Exception("ComfyUI server health check failed after maximum retries")
    
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
        # ComfyUI workflow thường là dict với node_id làm key
        return isinstance(workflow_data, dict) and len(workflow_data) > 0
    
    def _inject_input_data(self, workflow_data: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject input data vào workflow
        """
        try:
            prompt = input_data.get('prompt', '')
            width = input_data.get('w', 1024)
            height = input_data.get('h', 1024)
            
            logger.info(f"Injecting data: prompt='{prompt}', size={width}x{height}")
            
            # Tìm và inject data vào các node phù hợp
            for node_id, node in workflow_data.items():
                if 'inputs' in node:
                    inputs = node['inputs']
                    
                    # Inject text prompt
                    if 'text' in inputs and prompt:
                        inputs['text'] = prompt
                        logger.info(f"Injected text into node {node_id}")
                    
                    # Inject width
                    if 'width' in inputs:
                        inputs['width'] = width
                        logger.info(f"Injected width {width} into node {node_id}")
                    
                    # Inject height
                    if 'height' in inputs:
                        inputs['height'] = height
                        logger.info(f"Injected height {height} into node {node_id}")
                    
                    # Inject seed nếu có
                    if 'seed' in inputs and 'seed' in input_data:
                        inputs['seed'] = input_data['seed']
                        logger.info(f"Injected seed {input_data['seed']} into node {node_id}")
            
            return workflow_data
            
        except Exception as e:
            logger.error(f"Error injecting input data: {e}")
            return workflow_data
    
    async def _submit_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Submit workflow đến ComfyUI API"""
        try:
            payload = {
                "prompt": workflow_data,
                "client_id": "docker-worker"
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
                
                # Chờ 2 giây trước khi kiểm tra lại
                await asyncio.sleep(2)
                
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
                        
                        logger.info(f"Workflow completed with {len(result['outputs'])} output nodes")
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

# Global worker instance
worker = ComfyUIWorker()

async def process_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Xử lý một job từ API server
    
    Args:
        job_data: Dữ liệu job từ API server
        
    Returns:
        Kết quả xử lý
    """
    try:
        # Initialize worker nếu chưa
        if not worker.initialized:
            await worker.initialize()
        
        # Extract input data
        workflow_data = job_data.get('workflow')
        input_data = job_data.get('input', {})
        
        if not workflow_data:
            raise ValueError("No workflow data provided")
        
        # Process workflow
        result = await worker.process_workflow(workflow_data, input_data)
        
        return {
            'success': True,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"Job processing error: {e}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

def main():
    """
    Main function cho Docker worker
    Chạy như một background process
    """
    logger.info("Starting ComfyUI Docker Worker...")
    
    # Tạo event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Initialize worker
        loop.run_until_complete(worker.initialize())
        
        # Keep worker running
        logger.info("Worker is ready and running...")
        loop.run_forever()
        
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
    finally:
        # Cleanup
        loop.run_until_complete(worker.cleanup())
        loop.close()

if __name__ == "__main__":
    main()
