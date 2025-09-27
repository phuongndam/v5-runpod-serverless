import os
import logging
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ComfyUI Simple Monitor",
    description="Simple ComfyUI monitoring and control",
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

# ComfyUI configuration
COMFY_HOST = "127.0.0.1:8188"

def check_comfyui_status() -> Dict[str, Any]:
    """Check if ComfyUI is running and responsive"""
    try:
        response = requests.get(f"http://{COMFY_HOST}/", timeout=5)
        if response.status_code == 200:
            return {
                "status": "healthy",
                "message": "ComfyUI is running",
                "port": 8188,
                "timestamp": time.time()
            }
        else:
            return {
                "status": "error", 
                "message": f"ComfyUI returned status {response.status_code}",
                "port": 8188,
                "timestamp": time.time()
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"ComfyUI not reachable: {str(e)}",
            "port": 8188,
            "timestamp": time.time()
        }

@app.get("/ping")
async def health_check():
    """Health check endpoint for RunPod"""
    comfy_status = check_comfyui_status()
    return {
        "status": "healthy" if comfy_status["status"] == "healthy" else "error",
        "comfyui": comfy_status,
        "message": "ComfyUI Monitor is running"
    }

@app.get("/status")
async def get_status():
    """Get ComfyUI status"""
    return check_comfyui_status()

@app.post("/restart")
async def restart_comfyui():
    """Restart ComfyUI via supervisor"""
    try:
        # Call supervisor restart endpoint
        response = requests.post("http://127.0.0.1:8001/restart", timeout=30)
        if response.status_code == 200:
            return {"status": "success", "message": "ComfyUI restart requested"}
        else:
            return {"status": "error", "message": "Failed to restart ComfyUI"}
    except Exception as e:
        return {"status": "error", "message": f"Error restarting ComfyUI: {e}"}

@app.post("/stop")
async def stop_comfyui():
    """Stop ComfyUI via supervisor"""
    try:
        response = requests.post("http://127.0.0.1:8001/stop", timeout=30)
        if response.status_code == 200:
            return {"status": "success", "message": "ComfyUI stop requested"}
        else:
            return {"status": "error", "message": "Failed to stop ComfyUI"}
    except Exception as e:
        return {"status": "error", "message": f"Error stopping ComfyUI: {e}"}

@app.get("/metrics")
async def get_metrics():
    """Get basic system metrics"""
    try:
        # Get metrics from supervisor
        response = requests.get("http://127.0.0.1:8001/metrics", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Could not get metrics from supervisor"}
    except Exception as e:
        return {"error": f"Error getting metrics: {e}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8002"))  # Use port 8002 for monitoring app (avoid RunPod port 8000)
    uvicorn.run(app, host="0.0.0.0", port=port)