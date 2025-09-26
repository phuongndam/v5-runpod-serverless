import subprocess
import threading
import time
import os
import signal
import sys
import logging
from fastapi import FastAPI
import uvicorn

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
        self.running = False

    def start(self):
        """Khởi chạy ComfyUI nếu chưa chạy"""
        if self.process and self.process.poll() is None:
            logger.info("ComfyUI is already running (PID %s)", self.process.pid)
            return

        logger.info("Starting ComfyUI...")
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

        if self.autorestart:
            if not self.monitor_thread or not self.monitor_thread.is_alive():
                self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
                self.monitor_thread.start()

        logger.info("ComfyUI started with PID %s", self.process.pid)

    def stop(self):
        """Dừng ComfyUI (SIGTERM)"""
        if self.process and self.process.poll() is None:
            logger.info("Stopping ComfyUI (PID %s)", self.process.pid)
            os.kill(self.process.pid, signal.SIGTERM)
            self.process.wait()
        self.running = False
        self.process = None

    def kill(self):
        """Kill ComfyUI (SIGKILL)"""
        if self.process and self.process.poll() is None:
            logger.warning("Killing ComfyUI (PID %s)", self.process.pid)
            os.kill(self.process.pid, signal.SIGKILL)
            self.process.wait()
        self.running = False
        self.process = None

    def status(self):
        """Trả về trạng thái tiến trình"""
        if self.process and self.process.poll() is None:
            return {"status": "running", "pid": self.process.pid}
        return {"status": "stopped"}

    def _monitor(self):
        """Tự động restart nếu crash"""
        while self.running:
            if self.process and self.process.poll() is not None:
                logger.error("ComfyUI crashed! Restarting...")
                time.sleep(2)
                self.start()
            time.sleep(5)

# ----------------------------
# API Server (fake RunPod handler)
# ----------------------------
app = FastAPI()
manager = ComfyUIManager()

@app.on_event("startup")
def startup_event():
    logger.info("Handler startup: launching ComfyUI")
    manager.start()

@app.get("/status")
def get_status():
    return manager.status()

@app.post("/restart")
def restart():
    manager.stop()
    manager.start()
    return manager.status()

@app.post("/stop")
def stop():
    manager.stop()
    return manager.status()

@app.post("/kill")
def kill():
    manager.kill()
    return manager.status()

# ----------------------------
# Entry point
# ----------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)