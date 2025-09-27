import subprocess
import threading
import time
import os
import signal
import sys
import logging
import psutil
import requests
import json
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
from datetime import datetime, timedelta

# ----------------------------
# Logging setup
# ----------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("handler")

# ----------------------------
# Health Checker
# ----------------------------
class HealthChecker:
    def __init__(self, comfy_manager):
        self.comfy_manager = comfy_manager
        self.last_health_check = 0
        self.health_check_interval = 10  # seconds
        self.consecutive_failures = 0
        self.max_failures = 3
        
    def check_health(self) -> Dict[str, Any]:
        """Simple health check - only check if ComfyUI is running"""
        current_time = time.time()
        
        # Check if it's time for health check
        if current_time - self.last_health_check < self.health_check_interval:
            return {"status": "ok", "message": "Health check skipped (too recent)"}
        
        self.last_health_check = current_time
        
        # Check ComfyUI process
        if not self.comfy_manager.is_running():
            self.consecutive_failures += 1
            return {
                "status": "error", 
                "message": "ComfyUI process not running",
                "consecutive_failures": self.consecutive_failures
            }
        
        # Check ComfyUI HTTP endpoint with longer timeout for startup
        try:
            # Give ComfyUI more time to start up (30 seconds)
            response = requests.get(f"http://127.0.0.1:8188/", timeout=30)
            if response.status_code != 200:
                self.consecutive_failures += 1
                return {
                    "status": "error",
                    "message": f"ComfyUI HTTP returned status {response.status_code}",
                    "consecutive_failures": self.consecutive_failures
                }
        except Exception as e:
            # Don't count startup time as failure
            if "ComfyUI startup time" in str(e) or "Connection refused" in str(e):
                return {
                    "status": "starting",
                    "message": "ComfyUI is starting up",
                    "consecutive_failures": 0
                }
            
            self.consecutive_failures += 1
            return {
                "status": "error",
                "message": f"ComfyUI HTTP unreachable: {e}",
                "consecutive_failures": self.consecutive_failures
            }
        
        # Reset failure counter on success
        self.consecutive_failures = 0
        
        return {
            "status": "healthy",
            "message": "ComfyUI is running normally",
            "consecutive_failures": 0
        }
    
    def should_restart(self) -> bool:
        """Check if ComfyUI should be restarted"""
        return self.consecutive_failures >= self.max_failures

# ----------------------------
# ComfyUI Manager Class
# ----------------------------
class ComfyUIManager:
    def __init__(self,
                 python_bin="/environment-comfyui/venv/bin/python",
                 main_script="/ComfyUI/main.py",
                 port=8188,
                 autorestart=True):
        self.python_bin = python_bin
        self.main_script = main_script
        self.port = port
        self.autorestart = autorestart
        self.process = None
        self.monitor_thread = None
        self.health_thread = None
        self.running = False
        self.restart_count = 0
        self.max_restarts = 10
        self.last_restart = 0
        self.restart_cooldown = 60  # seconds

    def start(self):
        """Khởi chạy ComfyUI nếu chưa chạy"""
        if self.process and self.process.poll() is None:
            logger.info("ComfyUI is already running (PID %s)", self.process.pid)
            return True

        # Check restart limits
        current_time = time.time()
        if (self.restart_count >= self.max_restarts and 
            current_time - self.last_restart < self.restart_cooldown):
            logger.error("Max restarts reached, waiting for cooldown...")
            return False

        logger.info("Starting ComfyUI...")
        try:
            # Không redirect stdout/stderr sang PIPE -> tránh buffer full làm chết process
            self.process = subprocess.Popen(
                [
                    self.python_bin,
                    self.main_script,
                    "--listen", "0.0.0.0",
                    "--port", str(self.port),
                    "--disable-metadata",
                    "--disable-auto-launch",
                    "--verbose", os.getenv("COMFY_LOG_LEVEL", "DEBUG"),
                    "--log-stdout"
                ]
            )
            self.running = True
            self.restart_count += 1
            self.last_restart = current_time

            if self.autorestart:
                if not self.monitor_thread or not self.monitor_thread.is_alive():
                    self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
                    self.monitor_thread.start()

            logger.info("ComfyUI started with PID %s", self.process.pid)
            return True
        except Exception as e:
            logger.error(f"Failed to start ComfyUI: {e}")
            return False

    def stop(self):
        """Dừng ComfyUI (SIGTERM)"""
        if self.process and self.process.poll() is None:
            logger.info("Stopping ComfyUI (PID %s)", self.process.pid)
            try:
                os.kill(self.process.pid, signal.SIGTERM)
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("ComfyUI didn't stop gracefully, forcing kill...")
                    os.kill(self.process.pid, signal.SIGKILL)
                    self.process.wait()
            except ProcessLookupError:
                logger.warning("Process already terminated")
        self.running = False
        self.process = None

    def kill(self):
        """Kill ComfyUI (SIGKILL)"""
        if self.process and self.process.poll() is None:
            logger.warning("Killing ComfyUI (PID %s)", self.process.pid)
            try:
                os.kill(self.process.pid, signal.SIGKILL)
                self.process.wait()
            except ProcessLookupError:
                logger.warning("Process already terminated")
        self.running = False
        self.process = None

    def restart(self):
        """Restart ComfyUI"""
        logger.info("Restarting ComfyUI...")
        self.stop()
        time.sleep(2)  # Wait for cleanup
        return self.start()

    def is_running(self) -> bool:
        """Check if ComfyUI is running"""
        return (self.process is not None and 
                self.process.poll() is None and 
                self.running)

    def get_status(self) -> Dict[str, Any]:
        """Get detailed status"""
        status = {
            "running": self.is_running(),
            "pid": self.process.pid if self.process else None,
            "restart_count": self.restart_count,
            "last_restart": self.last_restart,
            "uptime": time.time() - self.last_restart if self.last_restart else 0
        }
        return status

    def _monitor(self):
        """Tự động restart nếu crash"""
        while self.running:
            if self.process and self.process.poll() is not None:
                logger.error("ComfyUI crashed! Restarting...")
                time.sleep(2)
                if not self.start():
                    logger.error("Failed to restart ComfyUI, stopping monitor...")
                    break
            time.sleep(5)

# ----------------------------
# API Server (ComfyUI Supervisor)
# ----------------------------
app = FastAPI(
    title="ComfyUI Supervisor",
    description="Health monitoring and management for ComfyUI workers",
    version="1.0.0"
)

# Global instances
manager = ComfyUIManager()
health_checker = HealthChecker(manager)
worker_id = os.getenv("WORKER_ID", f"worker_{os.getpid()}")

# Request models
class HealthResponse(BaseModel):
    status: str
    message: str
    consecutive_failures: Optional[int] = None
    timestamp: datetime

class WorkerInfo(BaseModel):
    worker_id: str
    status: str
    cpu_usage: float
    uptime: float
    restart_count: int

@app.on_event("startup")
async def startup_event():
    """Initialize ComfyUI and start monitoring"""
    logger.info("ComfyUI Supervisor starting...")
    
    # Start ComfyUI
    if not manager.start():
        logger.error("Failed to start ComfyUI on startup")
        return
    
    # Start health monitoring thread
    health_thread = threading.Thread(target=health_monitor_loop, daemon=True)
    health_thread.start()
    
    # Load balancer registration removed - not needed for simple monitoring
    
    logger.info("ComfyUI Supervisor started successfully")


def health_monitor_loop():
    """Background health monitoring loop - simple ComfyUI crash detection"""
    while True:
        try:
            # Perform health check
            health_result = health_checker.check_health()
            
            # Check if restart is needed (only if status is error, not starting)
            if health_result.get("status") == "error" and health_checker.should_restart():
                logger.warning("ComfyUI crashed or failed, restarting...")
                if manager.restart():
                    logger.info("ComfyUI restarted successfully")
                    health_checker.consecutive_failures = 0  # Reset after successful restart
                else:
                    logger.error("Failed to restart ComfyUI")
            elif health_result.get("status") == "starting":
                logger.info("ComfyUI is starting up, waiting...")
            elif health_result.get("status") == "healthy":
                logger.debug("ComfyUI is running normally")
                    
        except Exception as e:
            logger.error(f"Health monitor error: {e}")
        
        time.sleep(10)  # Check every 10 seconds (less frequent)


@app.get("/health", response_model=HealthResponse)
async def get_health():
    """Get current health status"""
    health_result = health_checker.check_health()
    return HealthResponse(
        status=health_result["status"],
        message=health_result["message"],
        consecutive_failures=health_result.get("consecutive_failures"),
        timestamp=datetime.now()
    )

@app.get("/status")
async def get_status():
    """Get ComfyUI status"""
    return manager.get_status()

@app.get("/worker_info", response_model=WorkerInfo)
async def get_worker_info():
    """Get detailed worker information"""
    cpu_usage = psutil.cpu_percent()
    status = manager.get_status()
    
    return WorkerInfo(
        worker_id=worker_id,
        status="healthy" if manager.is_running() else "error",
        cpu_usage=cpu_usage,
        uptime=status["uptime"],
        restart_count=status["restart_count"]
    )

@app.post("/restart")
async def restart_comfyui():
    """Manually restart ComfyUI"""
    logger.info("Manual restart requested")
    success = manager.restart()
    return {
        "status": "success" if success else "failed",
        "message": "ComfyUI restarted" if success else "Failed to restart ComfyUI"
    }

@app.post("/stop")
async def stop_comfyui():
    """Stop ComfyUI"""
    logger.info("Manual stop requested")
    manager.stop()
    return {"status": "stopped", "message": "ComfyUI stopped"}

@app.post("/kill")
async def kill_comfyui():
    """Force kill ComfyUI"""
    logger.warning("Manual kill requested")
    manager.kill()
    return {"status": "killed", "message": "ComfyUI killed"}

@app.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    
    return {
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "comfyui_running": manager.is_running(),
        "worker_id": worker_id,
        "timestamp": datetime.now().isoformat()
    }


# Workflow processing removed - this is handled by rp_handler.py independently

# ----------------------------
# Entry point
# ----------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)