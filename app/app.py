import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import requests
import time
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ComfyUI Load Balancer",
    description="Load balancer and health monitor for ComfyUI workers",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request models
class WorkflowRequest(BaseModel):
    workflow: dict
    images: Optional[List[dict]] = None
    priority: int = 1  # 1=normal, 2=high, 3=urgent

class WorkerStatus(BaseModel):
    worker_id: str
    status: str  # healthy, busy, error, offline
    last_ping: datetime
    current_jobs: int
    total_jobs: int
    cpu_usage: float

class LoadBalancerResponse(BaseModel):
    status: str
    message: str
    worker_id: Optional[str] = None
    estimated_wait_time: Optional[int] = None

# Global variables
workers: Dict[str, WorkerStatus] = {}
request_queue: List[WorkflowRequest] = []
request_count = 0
active_jobs: Dict[str, str] = {}  # job_id -> worker_id

# Worker management
WORKER_TIMEOUT = 30  # seconds
MAX_QUEUE_SIZE = 100
MAX_WORKERS = 5

@app.get("/ping")
async def health_check():
    """Health check endpoint for RunPod"""
    healthy_workers = sum(1 for w in workers.values() if w.status == "healthy")
    return {
        "status": "healthy",
        "workers": len(workers),
        "healthy_workers": healthy_workers,
        "queue_size": len(request_queue)
    }

@app.get("/workers")
async def get_workers():
    """Get status of all workers"""
    return {
        "workers": workers,
        "queue_size": len(request_queue),
        "active_jobs": len(active_jobs)
    }

@app.post("/register_worker")
async def register_worker(worker_id: str, status: str = "healthy"):
    """Register a new worker"""
    workers[worker_id] = WorkerStatus(
        worker_id=worker_id,
        status=status,
        last_ping=datetime.now(),
        current_jobs=0,
        total_jobs=0,
        cpu_usage=0.0
    )
    logger.info(f"Worker {worker_id} registered")
    return {"status": "registered", "worker_id": worker_id}

@app.post("/worker_heartbeat")
async def worker_heartbeat(worker_id: str, cpu_usage: float = 0.0):
    """Worker heartbeat to update status"""
    if worker_id in workers:
        workers[worker_id].last_ping = datetime.now()
        workers[worker_id].cpu_usage = cpu_usage
    
    return {"status": "heartbeat_received"}

@app.post("/job_completed")
async def job_completed(worker_id: str, job_id: str, success: bool = True):
    """Notify that a job has completed"""
    if worker_id in workers:
        workers[worker_id].current_jobs = max(0, workers[worker_id].current_jobs - 1)
        workers[worker_id].total_jobs += 1
        
        if job_id in active_jobs:
            del active_jobs[job_id]
    
    logger.info(f"Job {job_id} completed on worker {worker_id}, success: {success}")
    return {"status": "job_completed"}

def find_best_worker() -> Optional[str]:
    """Find the best available worker based on load"""
    available_workers = [
        (worker_id, worker) for worker_id, worker in workers.items()
        if worker.status == "healthy" and worker.current_jobs < 3
    ]
    
    if not available_workers:
        return None
    
    # Sort by current jobs and CPU usage
    available_workers.sort(key=lambda x: (x[1].current_jobs, x[1].cpu_usage))
    return available_workers[0][0]

@app.post("/submit_workflow", response_model=LoadBalancerResponse)
async def submit_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    """Submit a workflow to be processed"""
    global request_count
    request_count += 1
    
    # Check if queue is full
    if len(request_queue) >= MAX_QUEUE_SIZE:
        raise HTTPException(
            status_code=503, 
            detail="Queue is full, please try again later"
        )
    
    # Try to find an available worker
    worker_id = find_best_worker()
    
    if not worker_id:
        # Add to queue if no workers available
        request_queue.append(request)
        estimated_wait = len(request_queue) * 30  # Estimate 30s per job
        return LoadBalancerResponse(
            status="queued",
            message="No workers available, added to queue",
            estimated_wait_time=estimated_wait
        )
    
    # Assign job to worker
    job_id = f"job_{int(time.time())}_{request_count}"
    active_jobs[job_id] = worker_id
    workers[worker_id].current_jobs += 1
    
    # Forward request to worker
    background_tasks.add_task(forward_to_worker, worker_id, job_id, request)
    
    return LoadBalancerResponse(
        status="assigned",
        message=f"Job assigned to worker {worker_id}",
        worker_id=worker_id
    )

async def forward_to_worker(worker_id: str, job_id: str, request: WorkflowRequest):
    """Forward workflow request to specific worker"""
    try:
        worker_url = f"http://worker-{worker_id}:8188/process"
        payload = {
            "job_id": job_id,
            "workflow": request.workflow,
            "images": request.images
        }
        
        response = requests.post(worker_url, json=payload, timeout=300)
        response.raise_for_status()
        
        logger.info(f"Job {job_id} completed successfully on worker {worker_id}")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed on worker {worker_id}: {e}")
        # Mark worker as error and try to restart
        if worker_id in workers:
            workers[worker_id].status = "error"
        # TODO: Implement worker restart logic

async def cleanup_workers():
    """Periodically clean up inactive workers"""
    while True:
        current_time = datetime.now()
        inactive_workers = []
        
        for worker_id, worker in workers.items():
            time_since_ping = (current_time - worker.last_ping).total_seconds()
            if time_since_ping > WORKER_TIMEOUT:
                inactive_workers.append(worker_id)
        
        for worker_id in inactive_workers:
            logger.warning(f"Removing inactive worker {worker_id}")
            del workers[worker_id]
        
        await asyncio.sleep(10)  # Check every 10 seconds

@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup"""
    asyncio.create_task(cleanup_workers())
    logger.info("Load balancer started")

@app.get("/stats")
async def get_stats():
    """Get load balancer statistics"""
    return {
        "total_requests": request_count,
        "active_workers": len([w for w in workers.values() if w.status == "healthy"]),
        "queue_size": len(request_queue),
        "active_jobs": len(active_jobs),
        "workers": workers
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)