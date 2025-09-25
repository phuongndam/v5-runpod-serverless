"""
Test API Server cho ComfyUI Handler
API server để test giao tiếp với ComfyUI trong Docker
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiohttp
import uvicorn
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Khởi tạo FastAPI app
app = FastAPI(
    title="ComfyUI Test API",
    description="API để test ComfyUI handler trong Docker",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ComfyUI server URL (trong Docker)
COMFYUI_URL = "http://localhost:8188"

# Pydantic models
class Text2ImageRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    width: int = 832
    height: int = 1280
    steps: int = 8
    cfg: float = 1.0
    seed: Optional[int] = None
    batch_size: int = 1

class WorkflowRequest(BaseModel):
    workflow_data: Dict[str, Any]
    input_data: Optional[Dict[str, Any]] = {}

class ComfyUITestClient:
    """Client để giao tiếp với ComfyUI server"""
    
    def __init__(self):
        self.session = None
        self.workflow_template = None
        
    async def initialize(self):
        """Khởi tạo client"""
        self.session = aiohttp.ClientSession()
        await self._load_workflow_template()
        logger.info("ComfyUI Test Client initialized")
    
    async def _load_workflow_template(self):
        """Load workflow template từ file JSON"""
        try:
            workflow_path = Path("../workflow/text2image-nunchaku-flux.1-dev.json")
            if workflow_path.exists():
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    self.workflow_template = json.load(f)
                logger.info("Workflow template loaded successfully")
            else:
                logger.warning("Workflow template not found, using default")
        except Exception as e:
            logger.error(f"Error loading workflow template: {e}")
    
    async def check_health(self) -> bool:
        """Kiểm tra ComfyUI server có hoạt động không"""
        try:
            async with self.session.get(f"{COMFYUI_URL}/system_stats") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def submit_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Submit workflow đến ComfyUI"""
        try:
            payload = {
                "prompt": workflow_data,
                "client_id": "test-api-client"
            }
            
            async with self.session.post(
                f"{COMFYUI_URL}/prompt",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    prompt_id = result.get('prompt_id')
                    logger.info(f"Workflow submitted with prompt_id: {prompt_id}")
                    return prompt_id
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Failed to submit workflow: {error_text}"
                    )
        except Exception as e:
            logger.error(f"Error submitting workflow: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Chờ workflow hoàn thành"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Kiểm tra queue status
                async with self.session.get(f"{COMFYUI_URL}/queue") as response:
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
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_workflow_result(self, prompt_id: str) -> Dict[str, Any]:
        """Lấy kết quả workflow"""
        try:
            async with self.session.get(f"{COMFYUI_URL}/history/{prompt_id}") as response:
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
                                    # Lấy image URL
                                    image_url = f"{COMFYUI_URL}/view?filename={img_info['filename']}&type=output"
                                    images.append({
                                        'filename': img_info['filename'],
                                        'url': image_url,
                                        'type': img_info.get('type', 'output')
                                    })
                                
                                result['outputs'][node_id] = {
                                    'images': images
                                }
                        
                        return result
                    else:
                        raise HTTPException(status_code=404, detail="Prompt not found in history")
                else:
                    raise HTTPException(status_code=response.status, detail="Failed to get history")
                    
        except Exception as e:
            logger.error(f"Error getting workflow result: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def create_text2image_workflow(self, request: Text2ImageRequest) -> Dict[str, Any]:
        """Tạo workflow cho text2image từ template"""
        if not self.workflow_template:
            raise HTTPException(status_code=500, detail="Workflow template not loaded")
        
        # Copy workflow template
        workflow = json.loads(json.dumps(self.workflow_template))
        
        # Tìm và cập nhật các node cần thiết
        for node in workflow.get('nodes', []):
            node_type = node.get('type', '')
            
            # Cập nhật text prompt
            if node_type == 'CLIPTextEncode' and 'widgets_values' in node:
                node['widgets_values'][0] = request.prompt
            
            # Cập nhật kích thước
            elif node_type == 'PrimitiveNode' and node.get('title') == 'width':
                node['widgets_values'][0] = request.width
            elif node_type == 'PrimitiveNode' and node.get('title') == 'height':
                node['widgets_values'][0] = request.height
            
            # Cập nhật EmptySD3LatentImage
            elif node_type == 'EmptySD3LatentImage' and 'widgets_values' in node:
                node['widgets_values'] = [request.width, request.height, request.batch_size]
            
            # Cập nhật KSampler
            elif node_type == 'KSampler' and 'widgets_values' in node:
                seed = request.seed if request.seed is not None else "randomize"
                node['widgets_values'] = [
                    seed,
                    "randomize" if request.seed is None else request.seed,
                    request.steps,
                    request.cfg,
                    "euler",
                    "simple",
                    1.0
                ]
            
            # Cập nhật ModelSamplingFlux
            elif node_type == 'ModelSamplingFlux' and 'widgets_values' in node:
                node['widgets_values'] = [1.25, 0.5, request.width, request.height]
        
        return workflow
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

# Global client instance
client = ComfyUITestClient()

@app.on_event("startup")
async def startup_event():
    """Khởi tạo client khi server start"""
    await client.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup khi server shutdown"""
    await client.cleanup()

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ComfyUI Test API Server",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    is_healthy = await client.check_health()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "comfyui_connected": is_healthy
    }

@app.post("/text2image")
async def text2image(request: Text2ImageRequest):
    """Text to Image endpoint sử dụng workflow template"""
    try:
        # Kiểm tra ComfyUI health
        if not await client.check_health():
            raise HTTPException(status_code=503, detail="ComfyUI server not available")
        
        # Tạo workflow từ template
        workflow = client.create_text2image_workflow(request)
        
        # Submit workflow
        prompt_id = await client.submit_workflow(workflow)
        
        # Chờ completion
        result = await client.wait_for_completion(prompt_id)
        
        return {
            "success": True,
            "prompt_id": prompt_id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Text2Image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflow")
async def process_workflow(request: WorkflowRequest):
    """Process custom workflow"""
    try:
        # Kiểm tra ComfyUI health
        if not await client.check_health():
            raise HTTPException(status_code=503, detail="ComfyUI server not available")
        
        # Submit workflow
        prompt_id = await client.submit_workflow(request.workflow_data)
        
        # Chờ completion
        result = await client.wait_for_completion(prompt_id)
        
        return {
            "success": True,
            "prompt_id": prompt_id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Workflow processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue")
async def get_queue():
    """Lấy thông tin queue ComfyUI"""
    try:
        async with client.session.get(f"{COMFYUI_URL}/queue") as response:
            if response.status == 200:
                return await response.json()
            else:
                raise HTTPException(status_code=response.status, detail="Failed to get queue")
    except Exception as e:
        logger.error(f"Queue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{prompt_id}")
async def get_history(prompt_id: str):
    """Lấy history của một prompt"""
    try:
        async with client.session.get(f"{COMFYUI_URL}/history/{prompt_id}") as response:
            if response.status == 200:
                return await response.json()
            else:
                raise HTTPException(status_code=response.status, detail="Failed to get history")
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "test_api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
