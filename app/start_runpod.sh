#!/bin/bash

# Start script cho RunPod Serverless ComfyUI

echo "Starting ComfyUI Serverless on RunPod..."

# Activate virtual environment
source /environment-comfyui/venv/bin/activate

# Start ComfyUI server trong background
cd /workspace/ComfyUI
python main.py --listen 0.0.0.0 --port 8188 &
COMFYUI_PID=$!

# Chờ ComfyUI khởi động
echo "Waiting for ComfyUI to start..."
sleep 30

# Kiểm tra ComfyUI có chạy không
if ! curl -f http://localhost:8188/system_stats > /dev/null 2>&1; then
    echo "ComfyUI failed to start"
    exit 1
fi

echo "ComfyUI started successfully"

# Start RunPod handler
cd /workspace
python rp_handler.py
