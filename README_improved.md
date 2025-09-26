# 🚀 ComfyUI Serverless with Docker & RunPod

Dự án này đóng gói **ComfyUI** trong Docker, hỗ trợ chạy local hoặc deploy serverless (RunPod, GPU cloud).

## 📋 Mục lục

- [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Quick Start](#-quick-start)
- [Build & Deploy](#-build--deploy)
- [Sử dụng](#-sử-dụng)
- [API Endpoints](#-api-endpoints)
- [Troubleshooting](#-troubleshooting)

---

## 📂 Cấu trúc thư mục

```
workspace/
├── ComfyUI/                    # Source code chính của ComfyUI
├── .venv/                      # Virtual environment (Python 3.12)
├── Dockerfile                  # Dockerfile chính để build
├── Dockerfile-runpod          # Dockerfile dành cho RunPod serverless
├── docker-compose.yml         # Compose setup cho local test
├── rp_handler.py              # Serverless handler
├── start_runpod.sh            # Script khởi động RunPod
├── start_dev.sh               # Script development local
├── requirements-runpod.txt    # Dependencies cho RunPod
└── test-api-dev-local/        # Test environment
    ├── handler.py             # Handler test
    ├── runpod_mock_server.py  # Mock API server
    └── test_*.py              # Test scripts
```

---

## 🐳 Yêu cầu hệ thống

### Minimum Requirements
- **Docker Engine** >= 24.x
- **Docker Compose** plugin >= 2.x
- **RAM** >= 8GB (16GB recommended)
- **Storage** >= 20GB free space

### GPU Requirements (Optional)
- **GPU NVIDIA** (nếu chạy local với GPU)
- **Driver NVIDIA** + CUDA Toolkit (trên host)
- **VRAM** >= 8GB (12GB+ recommended)

---

## 🚀 Quick Start

### 1. Clone và Setup
```bash
git clone <repository-url>
cd comfyui-runpod-serverless
```

### 2. Chạy với Docker Compose
```bash
# Build và chạy
docker compose up

# Chạy nền
docker compose up -d

# Xem logs
docker compose logs -f
```

### 3. Truy cập ComfyUI
Mở trình duyệt: http://localhost:8188

---

## 🔧 Build & Deploy

### Local Development
```bash
# Build image
docker compose build

# Build mới hoàn toàn (bỏ cache)
docker compose build --no-cache

# Chạy container
docker compose up
```

### RunPod Deployment
```bash
# Build image cho RunPod
docker build -f Dockerfile-runpod -t your-image-name .

# Push lên registry
docker tag your-image-name your-registry/your-image-name
docker push your-registry/your-image-name
```

---

## 🐍 Sử dụng

### Virtual Environment
Trong container, Python và pip của venv đã được cài sẵn tại:
```bash
/workspace/.venv/bin/python
/workspace/.venv/bin/pip
```

### Chạy ComfyUI
```bash
# Chạy trực tiếp
/workspace/.venv/bin/python ComfyUI/main.py --listen 0.0.0.0 --port 8188

# Hoặc activate venv
source .venv/bin/activate
python ComfyUI/main.py --listen 0.0.0.0 --port 8188
```

### Development Mode
```bash
# Chạy development environment
./start_dev.sh start

# Test API
curl http://localhost:8000/health
```

---

## 🌐 API Endpoints

### ComfyUI Web Interface
- **URL**: http://localhost:8188
- **Description**: ComfyUI web interface

### Development API (Mock RunPod)
- **Health Check**: `GET http://localhost:8000/health`
- **API Docs**: `GET http://localhost:8000/docs`
- **Sync Generation**: `POST http://localhost:8000/runsync`
- **Async Generation**: `POST http://localhost:8000/run`

### Example API Usage
```bash
# Health check
curl http://localhost:8000/health

# Generate image (sync)
curl -X POST http://localhost:8000/runsync \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a beautiful landscape",
    "width": 1024,
    "height": 768
  }'
```

---

## 🔧 Container Management

### Basic Commands
```bash
# Start container
docker compose up

# Stop container
docker compose down

# Restart container
docker compose restart

# View logs
docker compose logs -f

# Exec into container
docker compose exec comfy-serverless-test bash
```

### Advanced Commands
```bash
# Remove everything (containers, volumes, networks)
docker compose down -v --remove-orphans

# Rebuild without cache
docker compose build --no-cache

# Run specific service
docker compose up comfy-serverless-test
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Container không start
```bash
# Check logs
docker compose logs

# Check port conflicts
lsof -i :8188
```

#### 2. GPU không hoạt động
```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.9.1-base-ubuntu24.04 nvidia-smi

# Check Docker GPU support
docker info | grep -i nvidia
```

#### 3. Out of Memory
```bash
# Check memory usage
docker stats

# Increase Docker memory limit in Docker Desktop
```

#### 4. Port already in use
```bash
# Find process using port
lsof -i :8188

# Kill process
kill -9 <PID>
```

### Debug Commands
```bash
# Check container status
docker compose ps

# Check container resources
docker stats comfy-serverless-test

# Check container logs
docker compose logs comfy-serverless-test

# Access container shell
docker compose exec comfy-serverless-test bash
```

---

## 📚 Additional Resources

- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [Docker Documentation](https://docs.docker.com/)
- [RunPod Documentation](https://docs.runpod.io/)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
