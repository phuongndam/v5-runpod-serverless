#!/usr/bin/env bash
set -e

# ----------------------------
# Environment setup
# ----------------------------
export PYTHONUNBUFFERED=1
export WORKER_ID="worker_$(hostname)_$$"

# ----------------------------
# Memory optimization with tcmalloc
# ----------------------------
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1 || true)"
if [ -n "$TCMALLOC" ]; then
    export LD_PRELOAD="${TCMALLOC}"
    echo "worker-comfyui: Using tcmalloc (${TCMALLOC})"
else
    echo "worker-comfyui: tcmalloc not found, continuing without it"
fi

# ----------------------------
# Force ComfyUI Manager to offline mode (if available)
# ----------------------------
if command -v comfy-manager-set-mode >/dev/null 2>&1; then
    comfy-manager-set-mode offline || \
      echo "worker-comfyui: Could not set ComfyUI-Manager network_mode" >&2
else
    echo "worker-comfyui: comfy-manager-set-mode not found, skipping..."
fi

# ----------------------------
# Default log level
# ----------------------------
: "${COMFY_LOG_LEVEL:=INFO}"

# ----------------------------
# Check if running in load balancer mode
# ----------------------------
if [ "${LOAD_BALANCER_MODE:-false}" = "true" ]; then
    echo "Starting in Load Balancer mode..."
    python -u /app/app.py
    exit 0
fi

# ----------------------------
# Start ComfyUI Supervisor (includes ComfyUI management)
# ----------------------------
echo "Starting ComfyUI Supervisor with auto-restart monitoring..."
python -u /app/handler.py &

SUPERVISOR_PID=$!
echo "ComfyUI Supervisor started with PID $SUPERVISOR_PID"

# Wait for supervisor to be ready
echo "Waiting for ComfyUI Supervisor to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "ComfyUI Supervisor is ready!"
        break
    fi
    echo "Waiting for supervisor... ($i/30)"
    sleep 2
done

# ----------------------------
# Start RunPod handler (main job dispatcher)
# ----------------------------
echo "Starting RunPod API handler..."
python -u /app/rp_handler.py &

RUNPOD_PID=$!
echo "RunPod handler started with PID $RUNPOD_PID"

# ----------------------------
# Wait for processes and handle cleanup
# ----------------------------
cleanup() {
    echo "Shutting down..."
    kill $SUPERVISOR_PID $RUNPOD_PID 2>/dev/null || true
    wait
    echo "Shutdown complete"
}

trap cleanup SIGTERM SIGINT

# Wait for any process to exit
wait