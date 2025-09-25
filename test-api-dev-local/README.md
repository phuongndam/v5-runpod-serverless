# ComfyUI RunPod Test Environment

Môi trường test để kiểm tra ComfyUI handler với API giả lập RunPod.

## Cấu trúc Files

- `handler.py` - ComfyUI handler chính để xử lý request
- `runpod_mock_server.py` - API server giả lập RunPod
- `test_handler_direct.py` - Test handler trực tiếp (không cần API server)
- `test_handler_api.py` - Test handler thông qua API server
- `test_docker_integration.py` - Test tích hợp với Docker container
- `start_test_environment.py` - Script khởi động môi trường test

## Cài đặt và Chạy

### 1. Cài đặt Dependencies

```bash
pip install -r requirements.txt
```

### 2. Chạy Test Environment

```bash
# Chạy interactive mode (khuyến nghị)
python start_test_environment.py

# Chạy test và thoát
python start_test_environment.py --no-interactive

# Chỉ chạy test (không start API server)
python start_test_environment.py --test-only
```

### 3. Test Riêng Lẻ

```bash
# Test handler trực tiếp
python test_handler_direct.py

# Test API server (cần chạy server trước)
python runpod_mock_server.py &
python test_handler_api.py

# Test Docker integration
python test_docker_integration.py
```

## API Endpoints

Khi API server chạy tại `http://localhost:8000`:

### Health Check
```bash
curl http://localhost:8000/health
```

### Synchronous Generation
```bash
curl -X POST http://localhost:8000/runsync \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a beautiful landscape with mountains and lake, sunset, photorealistic",
    "width": 1024,
    "height": 768
  }'
```

### Asynchronous Generation
```bash
# Submit job
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cute cat sitting on a windowsill",
    "width": 512,
    "height": 512
  }'

# Check job status (thay JOB_ID bằng ID trả về)
curl http://localhost:8000/status/JOB_ID
```

### List Jobs
```bash
curl http://localhost:8000/jobs
```

## Tham số Handler

Handler nhận các tham số sau trong `input`:

- `prompt` (string, required): Text prompt cho việc tạo ảnh
- `width` (int, required): Chiều rộng ảnh (64-2048 pixels)
- `height` (int, required): Chiều cao ảnh (64-2048 pixels)
- `seed` (int, optional): Random seed cho kết quả có thể tái tạo
- `steps` (int, optional): Số bước sampling (1-50, default: 8)
- `cfg` (float, optional): CFG scale (1.0-20.0, default: 1.0)

## Workflow Integration

Handler sẽ tự động cập nhật workflow `text2image-nunchaku-flux.1-dev.json` với:

1. **Node 6 (CLIPTextEncode)**: Cập nhật prompt text
2. **Node 34 (PrimitiveNode - width)**: Cập nhật chiều rộng
3. **Node 35 (PrimitiveNode - height)**: Cập nhật chiều cao
4. **Node 27 (EmptySD3LatentImage)**: Cập nhật kích thước latent
5. **Node 30 (ModelSamplingFlux)**: Cập nhật kích thước sampling

## Docker Testing

Để test với Docker container:

```bash
# Build Docker image
docker build -t comfyui-runpod-test -f ../Dockerfile ..

# Test handler trong container
python test_docker_integration.py
```

## Troubleshooting

### Lỗi "Module not found"
```bash
pip install -r requirements.txt
```

### Lỗi "Workflow file not found"
Đảm bảo file `../workflow-data/text2image-nunchaku-flux.1-dev.json` tồn tại.

### Lỗi "Port already in use"
```bash
# Tìm process đang sử dụng port 8000
lsof -i :8000

# Kill process
kill -9 PID
```

### Lỗi Docker
```bash
# Kiểm tra Docker daemon
docker --version
docker ps

# Rebuild image
docker build --no-cache -t comfyui-runpod-test -f ../Dockerfile ..
```

## Logs

- Handler logs: Console output
- API server logs: Console output hoặc check `http://localhost:8000/docs`
- Docker logs: `docker logs CONTAINER_ID`

## Ví dụ Response

### Thành công
```json
{
  "status": "success",
  "message": "Workflow updated successfully",
  "parameters": {
    "prompt": "a beautiful landscape with mountains and lake, sunset, photorealistic",
    "width": 1024,
    "height": 768
  },
  "workflow": {
    "id": "f253212e-0ec7-40c5-9671-bafc52d66023",
    "nodes": [...],
    "links": [...]
  }
}
```

### Lỗi
```json
{
  "status": "error",
  "error": "Missing required field: prompt"
}
```