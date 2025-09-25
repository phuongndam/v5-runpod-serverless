#!/bin/bash

# Start script cho ComfyUI Serverless Development

echo "Starting ComfyUI Serverless Development..."

# Start ComfyUI server trong background (sử dụng venv từ Docker image)
echo "Starting ComfyUI server..."
/environment-comfyui/venv/bin/python /ComfyUI/main.py --listen 0.0.0.0 --port 8188 --disable-auto-launch &
COMFYUI_PID=$!

# Chờ ComfyUI khởi động và load model xong
echo "Waiting for ComfyUI to start and load models..."
sleep 30

# Kiểm tra đơn giản xem ComfyUI process có đang chạy không
if ps aux | grep "main.py" | grep -v grep > /dev/null; then
    echo "ComfyUI process is running"
else
    echo "WARNING: ComfyUI process not found, but continuing with other servers..."
fi

# Start Worker Server (port 8001) - sử dụng uv venv
echo "Starting Worker Server on port 8001..."
cd /app-dev-test
python worker_server.py &
WORKER_PID=$!

# Chờ worker server khởi động
echo "Waiting for Worker Server to start..."
sleep 10

# Start API Server (port 8000) - sử dụng uv venv
echo "Starting API Server on port 8000..."
cd /app-dev-test
python api_server.py &
API_PID=$!

# Chờ API server khởi động
echo "Waiting for API Server to start..."
sleep 10

echo "Both servers are running:"
echo "  - API Server: http://localhost:8000"
echo "  - Worker Server: http://localhost:8001"
echo "  - ComfyUI: http://localhost:8188"

# Keep script running
wait