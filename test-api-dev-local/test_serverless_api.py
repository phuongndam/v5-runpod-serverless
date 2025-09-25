"""
Test Serverless API Server
FastAPI wrapper cho ComfyUI Serverless Handler
Mô phỏng cấu trúc RunPod Serverless nhưng không cần import runpod
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import handler từ test_serverless_handler
from test_serverless_handler import handler_sync, handler_async, load_workflow_template

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Khởi tạo FastAPI app
app = FastAPI(
    title="ComfyUI Serverless Test API",
    description="API test cho ComfyUI Serverless Handler (mô phỏng RunPod)",
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

# Pydantic models
class JobInput(BaseModel):
    """Job input model giống RunPod"""
    workflow: Dict[str, Any]
    input: Optional[Dict[str, Any]] = {}

class Text2ImageInput(BaseModel):
    """Text2Image input model"""
    prompt: str
    negative_prompt: Optional[str] = ""
    width: int = 832
    height: int = 1280
    steps: int = 8
    cfg: float = 1.0
    seed: Optional[int] = None
    batch_size: int = 1

class ServerlessResponse(BaseModel):
    """Response model giống RunPod"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    traceback: Optional[str] = None

# Global workflow template
workflow_template = None

@app.on_event("startup")
async def startup_event():
    """Load workflow template khi server start"""
    global workflow_template
    workflow_template = load_workflow_template()
    if workflow_template:
        logger.info("Workflow template loaded successfully")
    else:
        logger.warning("Workflow template not loaded")

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ComfyUI Serverless Test API",
        "version": "1.0.0",
        "status": "running",
        "description": "Mô phỏng RunPod Serverless Handler"
    }

@app.post("/runsync", response_model=ServerlessResponse)
async def run_sync(job_input: JobInput):
    """
    Run handler sync (giống RunPod serverless)
    """
    try:
        logger.info("Processing sync job...")
        
        # Convert Pydantic model to dict
        job_data = job_input.dict()
        
        # Run handler sync
        result = handler_sync(job_data)
        
        logger.info(f"Sync job completed: {result.get('success', False)}")
        return ServerlessResponse(**result)
        
    except Exception as e:
        logger.error(f"Sync job error: {e}")
        return ServerlessResponse(
            success=False,
            error=str(e)
        )

@app.post("/runasync", response_model=ServerlessResponse)
async def run_async(job_input: JobInput):
    """
    Run handler async (giống RunPod serverless)
    """
    try:
        logger.info("Processing async job...")
        
        # Convert Pydantic model to dict
        job_data = job_input.dict()
        
        # Run handler async
        result = await handler_async(job_data)
        
        logger.info(f"Async job completed: {result.get('success', False)}")
        return ServerlessResponse(**result)
        
    except Exception as e:
        logger.error(f"Async job error: {e}")
        return ServerlessResponse(
            success=False,
            error=str(e)
        )

@app.post("/text2image", response_model=ServerlessResponse)
async def text2image(request: Text2ImageInput):
    """
    Text2Image endpoint sử dụng workflow template
    """
    try:
        if not workflow_template:
            raise HTTPException(status_code=500, detail="Workflow template not loaded")
        
        # Tạo workflow từ template
        workflow = create_text2image_workflow(request)
        
        # Tạo job input
        job_input = JobInput(
            workflow=workflow,
            input={
                'text': request.prompt,
                'seed': request.seed
            }
        )
        
        # Run handler
        result = await handler_async(job_input.dict())
        
        return ServerlessResponse(**result)
        
    except Exception as e:
        logger.error(f"Text2Image error: {e}")
        return ServerlessResponse(
            success=False,
            error=str(e)
        )

def create_text2image_workflow(request: Text2ImageInput) -> Dict[str, Any]:
    """Tạo workflow cho text2image từ template"""
    if not workflow_template:
        raise ValueError("Workflow template not loaded")
    
    # Copy workflow template
    workflow = json.loads(json.dumps(workflow_template))
    
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

@app.get("/workflow/template")
async def get_workflow_template():
    """Lấy workflow template"""
    if workflow_template:
        return {
            "success": True,
            "template": workflow_template
        }
    else:
        return {
            "success": False,
            "error": "Workflow template not loaded"
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "workflow_loaded": workflow_template is not None
    }

# Test endpoints
@app.post("/test/sync")
async def test_sync():
    """Test sync handler với workflow template"""
    try:
        if not workflow_template:
            raise HTTPException(status_code=500, detail="Workflow template not loaded")
        
        # Test data
        job_input = JobInput(
            workflow=workflow_template,
            input={
                'text': 'test prompt for sync handler',
                'seed': 12345
            }
        )
        
        result = handler_sync(job_input.dict())
        return result
        
    except Exception as e:
        logger.error(f"Test sync error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/test/async")
async def test_async():
    """Test async handler với workflow template"""
    try:
        if not workflow_template:
            raise HTTPException(status_code=500, detail="Workflow template not loaded")
        
        # Test data
        job_input = JobInput(
            workflow=workflow_template,
            input={
                'text': 'test prompt for async handler',
                'seed': 54321
            }
        )
        
        result = await handler_async(job_input.dict())
        return result
        
    except Exception as e:
        logger.error(f"Test async error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        "test_serverless_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
