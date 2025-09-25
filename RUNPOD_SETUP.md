# ComfyUI Serverless trên RunPod

Hướng dẫn setup và sử dụng ComfyUI serverless trên RunPod.io

## 📁 Cấu trúc Files

```
.
├── rp_handler.py              # Main RunPod handler
├── Dockerfile-runpod          # Docker image cho RunPod
├── start_runpod.sh           # Start script
├── requirements-runpod.txt   # Python dependencies
├── test_runpod_handler.py    # Test script
└── ComfyUI/                  # ComfyUI source code
```

## 🚀 Setup trên RunPod

### 1. Build Docker Image

```bash
# Build image cho RunPod
docker build -f Dockerfile-runpod -t comfyui-serverless:latest .
```

### 2. Deploy lên RunPod

1. Đăng nhập vào [RunPod.io](https://runpod.io)
2. Tạo Serverless Endpoint mới
3. Upload Docker image hoặc sử dụng registry
4. Cấu hình:
   - **Container Image**: `comfyui-serverless:latest`
   - **Container Port**: `8188`
   - **Handler Path**: `/workspace/rp_handler.py`
   - **Max Workers**: `1` (recommended cho GPU intensive)
   - **Idle Timeout**: `300` seconds

### 3. Test Endpoint

```bash
curl -X POST https://your-endpoint-id-0-0.runpod.net/runsync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -d '{
    "input": {
      "workflow": {...},
      "input": {
        "text": "A beautiful landscape",
        "seed": 12345
      }
    }
  }'
```

## 📝 Sử dụng Handler

### Input Format

```json
{
  "workflow": {
    "nodes": [...],
    "links": [...],
    "groups": [],
    "config": {},
    "extra": {}
  },
  "input": {
    "text": "Your prompt here",
    "seed": 12345,
    "image_base64": "data:image/png;base64,..."
  }
}
```

### Output Format

```json
{
  "success": true,
  "result": {
    "prompt_id": "uuid-here",
    "status": "completed",
    "outputs": {
      "node_id": {
        "images": [
          {
            "filename": "ComfyUI_00001_.png",
            "base64": "base64-encoded-image",
            "type": "output"
          }
        ]
      }
    }
  }
}
```

## 🔧 Cấu hình

### Environment Variables

- `COMFYUI_URL`: URL của ComfyUI server (default: http://localhost:8188)
- `TIMEOUT`: Timeout cho workflow execution (default: 300s)
- `LOG_LEVEL`: Logging level (default: INFO)

### Custom Nodes

Handler tự động hỗ trợ các custom nodes có sẵn trong ComfyUI. Để thêm custom nodes mới:

1. Copy custom node vào `/workspace/ComfyUI/custom_nodes/`
2. Rebuild Docker image
3. Deploy lại

## 🧪 Testing

### Local Testing

```bash
# Test handler locally
python test_runpod_handler.py
```

### Production Testing

```bash
# Test với RunPod endpoint
curl -X POST YOUR_ENDPOINT_URL \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

## 📊 Monitoring

### Logs

Handler ghi logs chi tiết về:
- Workflow submission
- Execution progress
- Error handling
- Performance metrics

### Health Check

```bash
curl https://your-endpoint-id-0-0.runpod.net/health
```

## 🚨 Troubleshooting

### Common Issues

1. **ComfyUI không start**: Kiểm tra GPU memory và dependencies
2. **Workflow timeout**: Tăng timeout hoặc optimize workflow
3. **Memory issues**: Giảm batch size hoặc sử dụng CPU offload

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python rp_handler.py
```

## 💡 Tips

1. **Optimize Workflow**: Sử dụng efficient models và settings
2. **Memory Management**: Monitor GPU memory usage
3. **Caching**: Sử dụng model caching để tăng tốc
4. **Batch Processing**: Xử lý nhiều requests cùng lúc nếu có thể

## 📞 Support

- RunPod Documentation: https://docs.runpod.io
- ComfyUI Documentation: https://github.com/comfyanonymous/ComfyUI
- Issues: Tạo issue trên GitHub repository
