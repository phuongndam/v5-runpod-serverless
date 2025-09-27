#!/usr/bin/env bash
set -e

# ----------------------------
# Kill any existing processes first
# ----------------------------
echo "Cleaning up existing processes..."
pkill -f "python.*main.py" || true
pkill -f "python.*handler.py" || true
pkill -f "python.*rp_handler.py" || true
sleep 2

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
    # Check if running in simple monitoring mode (port 8002)
    # ----------------------------
    if [ "${MONITOR_MODE:-false}" = "true" ]; then
        echo "Starting in Simple Monitor mode on port 8002..."
        echo "Note: Port 8000 is reserved for RunPod serverless when deployed"
        python -u /app/app.py
        exit 0
    fi

    # ----------------------------
    # Start ComfyUI Supervisor (simple ComfyUI management only)
    # ----------------------------
    echo "Starting ComfyUI Supervisor for process management..."
    python -u /app/handler.py &

    SUPERVISOR_PID=$!
    echo "ComfyUI Supervisor started with PID $SUPERVISOR_PID"

    # Wait for supervisor to be ready
    echo "Waiting for ComfyUI Supervisor to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            echo "ComfyUI Supervisor is ready!"
            break
        fi
        echo "Waiting for supervisor... ($i/30)"
        sleep 2
    done

    # ----------------------------
    # Start RunPod handler (INDEPENDENT - main job dispatcher)
    # ----------------------------
    echo "Starting INDEPENDENT RunPod handler..."
    echo "This handler runs completely independently and handles all RunPod serverless logic"
    
    # Run rp_handler.py in the background, completely independent
    # For development: uses test_input.json if available
    python -u /app/rp_handler.py &

    RUNPOD_PID=$!
    echo "Independent RunPod handler started with PID $RUNPOD_PID"

    # ----------------------------
    # Optional: Start simple monitoring app on port 8002 (port 8000 reserved for RunPod serverless)
    # ----------------------------
    if [ "${START_MONITOR_APP:-true}" = "true" ]; then
        echo "Starting simple monitoring app on port 8002..."
        PORT=8002 python -u /app/app.py &
        MONITOR_PID=$!
        echo "Monitor app started with PID $MONITOR_PID"
    fi

    # ----------------------------
    # Wait for processes and handle cleanup
    # ----------------------------
    cleanup() {
        echo "Shutting down all processes..."
        # Kill all started processes
        kill $SUPERVISOR_PID $RUNPOD_PID ${MONITOR_PID:-} 2>/dev/null || true
        wait
        echo "Shutdown complete"
    }

    trap cleanup SIGTERM SIGINT

    # Wait for any process to exit
    wait