#!/usr/bin/env bash
set -e

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
# Force ComfyUI Manager to offline mode
# ----------------------------
comfy-manager-set-mode offline || \
  echo "worker-comfyui: Could not set ComfyUI-Manager network_mode" >&2

# ----------------------------
# Default log level = DEBUG
# ----------------------------
: "${COMFY_LOG_LEVEL:=INFO}"

# ----------------------------
# Start ComfyUI (background)
# ----------------------------
echo "worker-comfyui: Starting ComfyUI..."
/environment-comfyui/venv/bin/python /ComfyUI/main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --disable-metadata \
    --disable-auto-launch \
    --verbose "${COMFY_LOG_LEVEL}" \
    --log-stdout &

COMFYUI_PID=$!
echo "worker-comfyui: ComfyUI started with PID $COMFYUI_PID"

# ----------------------------
# Start handler (supervisor for ComfyUI)
# ----------------------------
echo "Starting ComfyUI Supervisor ..."
python -u /app/handler.py

# ----------------------------
# Start RunPod handler (main job dispatcher)
# ----------------------------
echo "Starting RunPod API handler ..."
python -u /app/runpod_handler.py