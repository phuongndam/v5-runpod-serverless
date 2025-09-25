# v5-runpod-serverless

Dự án này triển khai **ComfyUI** chạy ở chế độ serverless trên [RunPod](https://www.runpod.io), hỗ trợ xử lý AI (text2img, img2img, workflow JSON).

---

## 🚀 Yêu cầu

- **Docker** và **Docker Compose**
- GPU NVIDIA (khuyến nghị RTX 3090 trở lên)
- Tài khoản RunPod (nếu muốn deploy serverless)

---

## 📦 Cài đặt & Chạy local

Clone repo:
```bash
git clone https://github.com/phuongndam/v5-runpod-serverless.git
cd v5-runpod-serverless
```

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

## ⚙️ Cấu trúc thư mục

```
/workspace
 ├── .venv/                # Virtual environment (Python packages)
 ├── ComfyUI/              # Source code ComfyUI
 │   ├── custom_nodes/     # Custom nodes
 │   ├── models/           # Checkpoints, VAE, LoRA...
 ├── workflow-data/        # Lưu file workflow JSON (text2img, img2img...)
 ├── handler.py            # Serverless handler cho RunPod
 ├── comfy_infer.py        # Script headless gọi ComfyUI
 ├── docker-compose.yml
 ├── Dockerfile
 └── README.md
```

---

## ☁️ Deploy trên RunPod

1. Build image và push lên Docker Hub (hoặc GitHub Container Registry):
   ```bash
   docker build -t <your-dockerhub-username>/v5-runpod-serverless:latest .
   docker push <your-dockerhub-username>/v5-runpod-serverless:latest
   ```

2. Vào RunPod → Serverless → Tạo endpoint mới → nhập link image.

3. RunPod sẽ tự động khởi chạy `handler.py` để nhận request.

---

## 🛠️ Command hữu ích

- Kiểm tra logs:
  ```bash
  docker logs -f comfy-serverless-test
  ```

- Xóa container & image cũ:
  ```bash
  docker compose down --rmi all --volumes --remove-orphans
  ```

- Build lại sạch:
  ```bash
  docker compose build --no-cache
  ```

---

## 📜 License

MIT License – tự do sử dụng và tùy chỉnh.
