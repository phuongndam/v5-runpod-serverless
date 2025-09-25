#!/bin/bash

# Start script cho ComfyUI Serverless Development

echo "Starting ComfyUI Serverless Development..."

# Start ComfyUI server trong background (sử dụng venv đã cài sẵn)
echo "Starting ComfyUI server..."
/workspace/.venv/bin/python /workspace/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --disable-auto-launch &
COMFYUI_PID=$!

# Chờ ComfyUI khởi động
echo "Waiting for ComfyUI to start..."
sleep 60

# Kiểm tra ComfyUI có chạy không
echo "Checking ComfyUI health..."
if ! curl -f http://localhost:8188/system_stats > /dev/null 2>&1; then
    echo "ComfyUI failed to start"
    exit 1
fi

echo "ComfyUI started successfully on port 8188"

# Start Worker Server (port 8001) - sử dụng uv venv
echo "Starting Worker Server on port 8001..."
cd /dev
/opt/dev-venv/bin/python worker_server.py &
WORKER_PID=$!

# Chờ worker server khởi động
echo "Waiting for Worker Server to start..."
sleep 5

# Start API Server (port 8000) - sử dụng uv venv
echo "Starting API Server on port 8000..."
cd /dev
/opt/dev-venv/bin/python api_server.py &
API_PID=$!

# Chờ API server khởi động
echo "Waiting for API Server to start..."
sleep 5

echo "Both servers are running:"
echo "  - API Server: http://localhost:8000"
echo "  - Worker Server: http://localhost:8001"
echo "  - ComfyUI: http://localhost:8188"

# Keep script running
wait