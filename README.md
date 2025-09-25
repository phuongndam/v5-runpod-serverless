# v5-runpod-serverless

Dự án này triển khai **ComfyUI** chạy ở chế độ serverless trên [RunPod](https://www.runpod.io), hỗ trợ xử lý AI (text2img, img2img, workflow JSON).

---

## 🚀 Yêu cầu

- **Docker** và **Docker Compose**
- GPU NVIDIA (khuyến nghị RTX 3090 trở lên)
- Tài khoản RunPod (nếu muốn deploy serverless)
- **File `venv.tar.gz`** (xem hướng dẫn bên dưới)

---

## 📦 Cài đặt & Chạy local

### 1. Chuẩn bị file cần thiết

#### Tạo file `venv.tar.gz`:
```bash
# Tạo virtual environment từ Docker PyTorch (nếu chưa có)
docker run --rm -v ${PWD}:/workspace -w /workspace nvidia/cuda:12.1-devel-ubuntu22.04 bash -c "
    apt-get update && apt-get install -y python3.12 python3.12-venv python3-pip git
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    pip install -r ComfyUI/requirements.txt
"

# Nén virtual environment
tar -czf venv.tar.gz .venv
```

#### Tạo thư mục models (tùy chọn):
```bash
# Tạo thư mục models-mapping
mkdir -p models-mapping

# Tạo cấu trúc thư mục cho models
mkdir -p models-mapping/checkpoints
mkdir -p models-mapping/vae
mkdir -p models-mapping/loras
mkdir -p models-mapping/controlnet
mkdir -p models-mapping/upscale_models
```

### 2. Clone và setup

Clone repo:
```bash
git clone https://github.com/phuongndam/v5-runpod-serverless.git
cd v5-runpod-serverless
```

### 3. Build và chạy

Build Docker image (không cache):
```bash
docker compose build --no-cache
```

Chạy container:
```bash
docker compose up
```

Mặc định service sẽ chạy tại:  
👉 [http://localhost:8188](http://localhost:8188)

---

## 🎯 Models Setup (Tùy chọn)

### Download models FLUX và SDXL:

#### FLUX Models:
```bash
# FLUX.1-dev (Text-to-Image)
wget -O models-mapping/checkpoints/flux1-dev.safetensors https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors

# FLUX.1-dev VAE
wget -O models-mapping/vae/flux1-dev-vae.safetensors https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors
```

#### SDXL Models:
```bash
# SDXL Base Model
wget -O models-mapping/checkpoints/sdxl_base.safetensors https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors

# SDXL VAE
wget -O models-mapping/vae/sdxl_vae.safetensors https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors

# SDXL Refiner
wget -O models-mapping/checkpoints/sdxl_refiner.safetensors https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors
```

### Cấu hình models trong Docker:

Tạo file `src/extra_model_paths.yaml`:
```yaml
checkpoints:
  - /workspace/models-mapping/checkpoints
vae:
  - /workspace/models-mapping/vae
loras:
  - /workspace/models-mapping/loras
controlnet:
  - /workspace/models-mapping/controlnet
upscale_models:
  - /workspace/models-mapping/upscale_models
```

---

## ⚙️ Cấu trúc thư mục

```
/workspace
 ├── .venv/                # Virtual environment (Python packages)
 ├── venv.tar.gz           # Nén virtual environment cho Docker
 ├── ComfyUI/              # Source code ComfyUI
 │   ├── custom_nodes/     # Custom nodes
 │   ├── models/           # Checkpoints, VAE, LoRA...
 ├── models-mapping/       # Models từ host (tùy chọn)
 │   ├── checkpoints/      # FLUX, SDXL checkpoints
 │   ├── vae/             # VAE models
 │   ├── loras/           # LoRA models
 │   └── controlnet/      # ControlNet models
 ├── workflow-data/        # Lưu file workflow JSON
 ├── src/
 │   └── extra_model_paths.yaml  # Cấu hình model paths
 ├── app-dev-test/         # Development scripts
 ├── docker-compose.yml
 ├── Dockerfile
 └── README.md
```

---

## 🧪 Testing

### Test ComfyUI API:
```bash
# Chạy test script
cd app-dev-test
python test_api.py
```

### Test với workflow JSON:
```bash
# Test workflow từ file
curl -X POST http://localhost:8188/prompt \
  -H "Content-Type: application/json" \
  -d @workflow-data/text2image-nunchaku-flux.1-dev.json
```

---

## ☁️ Deploy trên RunPod

1. Build image và push lên Docker Hub:
   ```bash
   docker build -t <your-dockerhub-username>/v5-runpod-serverless:latest .
   docker push <your-dockerhub-username>/v5-runpod-serverless:latest
   ```

2. Vào RunPod → Serverless → Tạo endpoint mới → nhập link image.

3. RunPod sẽ tự động khởi chạy handler để nhận request.

---

## 🛠️ Command hữu ích

- Kiểm tra logs:
  ```bash
  docker logs -f v5-runpod-serverless-comfyui-worker-1
  ```

- Xóa container & image cũ:
  ```bash
  docker compose down --rmi all --volumes --remove-orphans
  ```

- Build lại sạch:
  ```bash
  docker compose build --no-cache
  ```

- Vào container để debug:
  ```bash
  docker compose exec comfyui-worker bash
  ```

---

## 🔧 Troubleshooting

### Lỗi "venv.tar.gz not found":
- Đảm bảo đã tạo file `venv.tar.gz` từ `.venv` hiện tại
- Kiểm tra file có tồn tại trong thư mục gốc

### Lỗi "Models not found":
- Kiểm tra file `src/extra_model_paths.yaml` có đúng cấu hình
- Đảm bảo models đã được download vào `models-mapping/`

### Lỗi "Permission denied":
- Chạy `chmod +x app-dev-test/start_dev.sh`
- Kiểm tra quyền truy cập thư mục

---

## 📜 License

MIT License – tự do sử dụng và tùy chỉnh.