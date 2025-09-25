#!/bin/bash

# Start script cho ComfyUI Serverless Development

echo "Starting ComfyUI Serverless Development..."

# Start ComfyUI server trong background (sử dụng venv đã cài sẵn)
echo "Starting ComfyUI server..."
/workspace/.venv/bin/python /workspace/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --disable-auto-launch &
COMFYUI_PID=$!

# Chờ ComfyUI khởi động và kiểm tra health check
echo "Waiting for ComfyUI to start..."
MAX_ATTEMPTS=10
ATTEMPT=1
SLEEP_INTERVAL=30

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    echo "Health check attempt $ATTEMPT/$MAX_ATTEMPTS..."
    
    if curl -f http://localhost:8188/system_stats > /dev/null 2>&1; then
        echo "ComfyUI started successfully on port 8188"
        break
    fi
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo "ComfyUI failed to start after $MAX_ATTEMPTS attempts"
        exit 1
    fi
    
    echo "ComfyUI not ready yet, waiting $SLEEP_INTERVAL seconds..."
    sleep $SLEEP_INTERVAL
    ATTEMPT=$((ATTEMPT + 1))
done

# Start Worker Server (port 8001) - sử dụng uv venv
echo "Starting Worker Server on port 8001..."
cd /app-dev-test
/opt/dev-venv/bin/python worker_server.py &
WORKER_PID=$!

# Chờ worker server khởi động
echo "Waiting for Worker Server to start..."
sleep 5

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