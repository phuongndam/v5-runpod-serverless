#!/bin/bash

# Start script cho ComfyUI Serverless Development

echo "Starting ComfyUI Serverless Development..."

# Start ComfyUI server trong background (sử dụng venv từ Docker image)
echo "Starting ComfyUI server..."
/environment-comfyui/venv/bin/python /workspace/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --disable-auto-launch &
COMFYUI_PID=$!

# Chờ ComfyUI khởi động và kiểm tra health check
echo "Waiting for ComfyUI to start..."

counter=0
while [ $counter -le 19 ]; do
    echo "Health check attempt $counter..."
    
    # Check if ComfyUI process is running and port is listening
    if ps aux | grep "main.py" | grep -v grep > /dev/null && netstat -tlnp 2>/dev/null | grep 8188 > /dev/null; then
        # Additional check: try to get a response from ComfyUI
        if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8188/system_stats/ | grep -q 200; then
            echo "ComfyUI started successfully on port 8188"
            break
        fi
    fi
    
    if [ $counter -eq 19 ]; then
        echo "ComfyUI failed to start after 20 attempts"
        exit 1
    fi
    
    echo "ComfyUI not ready yet, waiting 20 seconds..."
    sleep 20
    counter=$((counter + 1))
done

# Start Worker Server (port 8001) - sử dụng uv venv
echo "Starting Worker Server on port 8001..."
cd /app-dev-test
/opt/dev-venv/bin/python worker_server.py &
WORKER_PID=$!

# Chờ worker server khởi động
echo "Waiting for Worker Server to start..."
sleep 20

# Start API Server (port 8000) - sử dụng uv venv
echo "Starting API Server on port 8000..."
cd /app-dev-test
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