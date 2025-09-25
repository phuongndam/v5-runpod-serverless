@echo off
echo Testing ComfyUI API from Windows...
echo.

echo 1. Testing health check...
curl http://localhost:8000/health
echo.
echo.

echo 2. Testing image generation...
curl -X POST http://localhost:8000/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\": \"a beautiful landscape with mountains and lake\", \"w\": 1024, \"h\": 768}"
echo.
echo.

echo Test completed!
pause
