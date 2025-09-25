# ComfyUI Docker Worker

## Cấu trúc hệ thống

```
Windows Host
    ↓ curl POST
API Server (port 8000)
    ↓ HTTP POST
Worker Server (port 8001)
    ↓ ComfyUI API
ComfyUI (port 8188)
```

## Cài đặt dependencies

### 1. Cài đặt cho Docker container
- **ComfyUI**: Chạy với `/environment-comfyui/venv/bin/python` (dependencies từ Docker image)
- **Dev programs**: Chạy với uv virtual environment `/opt/dev-venv/bin/python` với dependencies từ `/dev/requirements-dev.txt`

### 2. Cài đặt cho development local (Windows) - Tùy chọn
```bash
pip install -r dev/requirements-dev.txt
```

## Cách chạy

### 1. Build và chạy container
```bash
docker-compose up --build
```

### 2. Test API từ Windows
```bash
# Health check
curl http://localhost:8000/health

# Generate image
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a beautiful landscape", "w": 1024, "h": 768}'
```

### 3. Test bằng Python script
```bash
python dev/test_api.py
```

## Endpoints

### API Server (port 8000)
- `GET /health` - Health check
- `POST /generate` - Generate image

### Worker Server (port 8001)
- `GET /health` - Health check
- `POST /process` - Process job

### ComfyUI (port 8188)
- ComfyUI web interface
- ComfyUI API endpoints

## Workflow

1. **Windows host** gửi curl request đến API Server (uv venv)
2. **API Server** load workflow template và gửi đến Worker Server (uv venv)
3. **Worker Server** xử lý với ComfyUI (workspace venv) và trả về kết quả
4. **API Server** trả về kết quả cho Windows host

## Files quan trọng

- `dev/start_dev.sh` - Script khởi động chính
- `dev/api_server.py` - API Server nhận curl requests
- `dev/worker_server.py` - Worker Server xử lý ComfyUI
- `dev/rp_handler.py` - ComfyUI Worker logic
- `dev/test_api.py` - Script test API
- `dev/requirements-dev.txt` - Dependencies cho Docker container và development local
- `dev/run_test.bat` - Test script cho Windows
- `workflow-data/text2image-nunchaku-flux.1-dev.json` - Workflow template

## Cấu trúc thư mục

```
dev/
├── start_dev.sh          # Script khởi động
├── api_server.py         # API Server (port 8000)
├── worker_server.py      # Worker Server (port 8001)
├── rp_handler.py         # ComfyUI Worker logic
├── test_api.py           # Test script Python
├── run_test.bat          # Test script Windows
├── requirements-dev.txt  # Dependencies cho Docker và local dev
└── README.md             # Hướng dẫn này
```
