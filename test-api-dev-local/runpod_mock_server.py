#!/usr/bin/env python3
"""
Mock RunPod Serverless API Server
Simulates RunPod's serverless API for testing ComfyUI handlers locally
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import os
import sys

# Add parent directory to path to import handler
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    import uvicorn
except ImportError:
    print("Installing required packages...")
    os.system("pip install fastapi uvicorn pydantic")
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    import uvicorn

# Import our handler
from handler import handler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Mock RunPod Serverless API",
    description="Simulates RunPod serverless API for testing ComfyUI handlers",
    version="1.0.0"
)

# Pydantic models for request/response
class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt for image generation", min_length=1)
    width: int = Field(..., description="Image width in pixels", ge=64, le=2048)
    height: int = Field(..., description="Image height in pixels", ge=64, le=2048)
    seed: Optional[int] = Field(None, description="Random seed for reproducible results")
    steps: Optional[int] = Field(8, description="Number of sampling steps", ge=1, le=50)
    cfg: Optional[float] = Field(1.0, description="CFG scale", ge=1.0, le=20.0)

class JobStatus(BaseModel):
    id: str
    status: str  # "IN_QUEUE", "IN_PROGRESS", "COMPLETED", "FAILED"
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# In-memory job storage (in production, use Redis or database)
jobs_db: Dict[str, JobStatus] = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Mock RunPod Serverless API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/runsync")
async def run_sync(request: GenerateRequest):
    """
    Synchronous execution endpoint (simulates RunPod's runsync)
    """
    try:
        logger.info(f"Received sync request: {request.dict()}")
        
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Prepare event data in RunPod format
        event_data = {
            "input": {
                "prompt": request.prompt,
                "width": request.width,
                "height": request.height,
                "seed": request.seed,
                "steps": request.steps,
                "cfg": request.cfg
            }
        }
        
        # Execute handler
        logger.info(f"Executing handler for job {job_id}")
        result = handler(event_data)
        
        # Check if handler returned an error
        if result.get("status") == "error":
            logger.error(f"Handler error for job {job_id}: {result.get('error')}")
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        logger.info(f"Job {job_id} completed successfully")
        
        return {
            "id": job_id,
            "status": "COMPLETED",
            "output": result,
            "executionTime": "0.5s"  # Mock execution time
        }
        
    except Exception as e:
        logger.error(f"Error in runsync: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/run")
async def run_async(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Asynchronous execution endpoint (simulates RunPod's run)
    """
    try:
        logger.info(f"Received async request: {request.dict()}")
        
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Create job status
        job_status = JobStatus(
            id=job_id,
            status="IN_QUEUE",
            created_at=datetime.now().isoformat()
        )
        jobs_db[job_id] = job_status
        
        # Add background task
        background_tasks.add_task(process_job_async, job_id, request)
        
        logger.info(f"Job {job_id} queued for processing")
        
        return {
            "id": job_id,
            "status": "IN_QUEUE"
        }
        
    except Exception as e:
        logger.error(f"Error in run: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def process_job_async(job_id: str, request: GenerateRequest):
    """
    Background task to process job asynchronously
    """
    try:
        logger.info(f"Processing job {job_id} in background")
        
        # Update job status
        jobs_db[job_id].status = "IN_PROGRESS"
        
        # Prepare event data
        event_data = {
            "input": {
                "prompt": request.prompt,
                "width": request.width,
                "height": request.height,
                "seed": request.seed,
                "steps": request.steps,
                "cfg": request.cfg
            }
        }
        
        # Execute handler
        result = handler(event_data)
        
        # Update job status
        if result.get("status") == "error":
            jobs_db[job_id].status = "FAILED"
            jobs_db[job_id].error = result.get("error")
            logger.error(f"Job {job_id} failed: {result.get('error')}")
        else:
            jobs_db[job_id].status = "COMPLETED"
            jobs_db[job_id].result = result
            jobs_db[job_id].completed_at = datetime.now().isoformat()
            logger.info(f"Job {job_id} completed successfully")
            
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
        jobs_db[job_id].status = "FAILED"
        jobs_db[job_id].error = str(e)
        jobs_db[job_id].completed_at = datetime.now().isoformat()

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Get job status endpoint
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_db[job_id]
    return {
        "id": job.id,
        "status": job.status,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "result": job.result,
        "error": job.error
    }

@app.get("/jobs")
async def list_jobs():
    """
    List all jobs endpoint
    """
    return {
        "jobs": [
            {
                "id": job.id,
                "status": job.status,
                "created_at": job.created_at,
                "completed_at": job.completed_at
            }
            for job in jobs_db.values()
        ]
    }

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete job endpoint
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    del jobs_db[job_id]
    return {"message": f"Job {job_id} deleted successfully"}

if __name__ == "__main__":
    print("Starting Mock RunPod Serverless API Server...")
    print("API Documentation available at: http://localhost:8000/docs")
    print("Health check: http://localhost:8000/health")
    print("\nExample usage:")
    print("curl -X POST 'http://localhost:8000/runsync' \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"prompt\": \"a beautiful landscape\", \"width\": 1024, \"height\": 768}'")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
