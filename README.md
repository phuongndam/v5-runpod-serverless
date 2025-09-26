# 🚀 RunPod Serverless ComfyUI FLUX Worker

A high-performance, production-ready RunPod serverless worker for ComfyUI with optimized FLUX model support using ComfyUI-Nunchaku quantization.

## ✨ Features

### 🎨 **Advanced FLUX Support**
- **Quantized FLUX Models**: INT4 quantization for faster inference
- **AWQ Text Encoders**: Optimized T5XXL and CLIP encoders
- **Multiple FLUX Variants**: Dev, Schnell, and Turbo Alpha support
- **Professional LoRAs**: Super Realism and Turbo Alpha integration

### ⚡ **Performance Optimizations**
- **20-minute timeout** for complex workflows
- **Auto-restart** on crashes with health monitoring
- **Memory-efficient** model loading and caching
- **GPU-optimized** inference pipeline

### 🔧 **Enhanced Functionality**
- **ComfyUI-Nunchaku**: Advanced model quantization and optimization
- **ComfyUI-Easy-Use**: Streamlined UI and workflow management
- **ComfyUI-Impact-Pack**: Professional image processing tools
- **Ultimate SD Upscale**: High-quality image upscaling
- **rgthree-comfy**: Advanced workflow utilities

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   RunPod API    │───▶│  rp_handler.py   │───▶│  handler.py     │
│   (External)    │    │  (Job Router)    │    │  (Supervisor)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │    ComfyUI      │
                                               │  (Port 8188)    │
                                               └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- NVIDIA GPU with CUDA support
- RunPod account and API key

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd v5-runpod-serverless
```

### 2. Setup Models
Place your models in the `models-mapping` directory:
```
models-mapping/
├── models/
│   ├── checkpoints/
│   │   └── svdq-int4_r32-flux.1-dev.safetensors
│   ├── text_encoders/
│   │   ├── awq-int4-flux.1-t5xxl.safetensors
│   │   └── clip_l.safetensors
│   ├── vae/
│   │   └── ae.safetensors
│   └── loras/
│       ├── FLUX.1-Turbo-Alpha.safetensors
│       └── flux-super-realism.safetensors
```

### 3. Build and Run
```bash
# Build Docker image
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 4. Test Workflow
```bash
# Test locally
python test_workflow_direct.py

# Test with Docker
python test_workflow_docker.py
```

## 📋 API Usage

### Request Format
```json
{
  "input": {
    "workflow": {
      "6": {
        "inputs": {
          "text": "magazine cover photo of a black supermodel, full body shot, low angle view from her feet, wide-angle lens, watching the sunset, hyperrealistic, vogue style",
          "clip": ["57", 0]
        },
        "class_type": "CLIPTextEncode"
      },
      // ... more nodes
    }
  }
}
```

### Response Format
```json
{
  "images": [
    {
      "filename": "RunPod_Test_00001.png",
      "type": "base64",
      "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    }
  ],
  "status": "success"
}
```

## 🎯 Supported Workflows

### FLUX Text-to-Image
- **Resolution**: 832x1280 (portrait), 1280x832 (landscape)
- **Steps**: 8 (optimized for speed)
- **Sampler**: Euler
- **CFG**: 1.0
- **Guidance**: 3.5

### Model Requirements
| Model Type | File Name | Size | Description |
|------------|-----------|------|-------------|
| **FLUX DiT** | `svdq-int4_r32-flux.1-dev.safetensors` | ~2.5GB | Quantized FLUX model |
| **T5 Encoder** | `awq-int4-flux.1-t5xxl.safetensors` | ~1.2GB | AWQ quantized text encoder |
| **CLIP Encoder** | `clip_l.safetensors` | ~246MB | CLIP text encoder |
| **VAE** | `ae.safetensors` | ~335MB | FLUX VAE |
| **LoRA** | `FLUX.1-Turbo-Alpha.safetensors` | ~1.4GB | Turbo Alpha LoRA |
| **LoRA** | `flux-super-realism.safetensors` | ~1.4GB | Super Realism LoRA |

## 🔧 Configuration

### Environment Variables
```bash
# ComfyUI Configuration
COMFY_LOG_LEVEL=DEBUG
COMFY_HOST=127.0.0.1:8188
SUPERVISOR_HOST=127.0.0.1:8000

# RunPod Configuration
REFRESH_WORKER=false
WEBSOCKET_RECONNECT_ATTEMPTS=5
WEBSOCKET_RECONNECT_DELAY_S=3
```

### Docker Compose
```yaml
services:
  comfyui-worker:
    image: phuongndam/comfyuiworker:v1.0.2
    ports:
      - "8188:8188"  # ComfyUI
      - "8000:8000"  # Supervisor
    volumes:
      - ./models-mapping:/runpod-volume
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

## 🧪 Testing

### Local Testing
```bash
# Test ComfyUI directly
python test_workflow_direct.py

# Test with Docker environment detection
python test_workflow_docker.py
```

### Test Workflow
The included `test_new_workflow.json` contains a verified FLUX workflow that generates:
- **Prompt**: Magazine cover photo with professional styling
- **Resolution**: 832x1280 portrait
- **Style**: Hyperrealistic, Vogue-style photography
- **Generation Time**: ~2-3 minutes on RTX 4090

## 📊 Performance

### Benchmarks (RTX 4090)
| Task | Time | Memory |
|------|------|--------|
| **Model Loading** | ~30s | ~8GB |
| **Image Generation** | ~2-3min | ~12GB |
| **Total Workflow** | ~3-4min | Peak 12GB |

### Optimization Features
- ✅ **Quantized Models**: 4x smaller, 2x faster
- ✅ **Smart Caching**: Reduced model reload times
- ✅ **Memory Management**: Efficient GPU memory usage
- ✅ **Auto-restart**: Robust error recovery

## 🚀 Deployment

### RunPod Serverless
1. **Build Image**: `docker build -t your-registry/comfyui-flux:latest .`
2. **Push to Registry**: `docker push your-registry/comfyui-flux:latest`
3. **Create Endpoint**: Use the image in RunPod serverless
4. **Upload Models**: Place models in RunPod storage
5. **Test**: Use the provided workflow JSON

### Production Checklist
- [ ] All required models uploaded
- [ ] GPU memory sufficient (16GB+ recommended)
- [ ] Network connectivity verified
- [ ] Health monitoring enabled
- [ ] Error handling tested

## 🛠️ Development

### Project Structure
```
├── app/
│   ├── handler.py          # ComfyUI supervisor
│   ├── rp_handler.py       # RunPod handler
│   └── start.sh           # Startup script
├── custom_nodes/          # ComfyUI extensions
├── models-mapping/        # Model storage
├── workflow-data/         # Example workflows
├── test_*.py             # Testing scripts
└── docker-compose.yml    # Docker configuration
```

### Adding New Workflows
1. Export workflow from ComfyUI
2. Test with `test_workflow_direct.py`
3. Add to `workflow-data/` directory
4. Update documentation

## 🐛 Troubleshooting

### Common Issues

**Q: Workflow times out after 20 minutes**
- A: Check GPU memory usage, reduce batch size or resolution

**Q: Models not found**
- A: Verify model files are in `models-mapping/models/` directory

**Q: ComfyUI not starting**
- A: Check Docker logs: `docker-compose logs comfyui-worker`

**Q: Low quality output**
- A: Ensure all LoRAs are loaded correctly, check prompt quality

### Debug Mode
```bash
# Enable verbose logging
export COMFY_LOG_LEVEL=DEBUG
export WEBSOCKET_TRACE=true

# Check health status
curl http://localhost:8000/health
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: [Wiki](https://github.com/your-repo/wiki)
- **Discord**: [Community Server](https://discord.gg/your-server)

## 🙏 Acknowledgments

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - The amazing workflow engine
- [ComfyUI-Nunchaku](https://github.com/your-nunchaku-repo) - Model optimization
- [RunPod](https://runpod.io) - Serverless GPU platform
- [FLUX](https://stability.ai) - The incredible diffusion model

---

**Made with ❤️ for the AI art community**

*Ready to create stunning images at scale! 🎨✨*