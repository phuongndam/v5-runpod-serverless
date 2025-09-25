#!/usr/bin/env python3
"""
Script để start ComfyUI Serverless Test API
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Start serverless test API server"""
    
    # Đảm bảo đang ở đúng directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("🚀 Starting ComfyUI Serverless Test API...")
    print(f"📁 Working directory: {os.getcwd()}")
    print("🔧 Mô phỏng RunPod Serverless Handler")
    
    # Kiểm tra requirements
    try:
        import fastapi
        import uvicorn
        import aiohttp
        print("✅ Dependencies OK")
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("📦 Installing requirements...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Start server
    print("\n🌐 Starting server on http://localhost:8000")
    print("📖 API docs available at http://localhost:8000/docs")
    print("🔍 Health check at http://localhost:8000/health")
    print("\n📋 Available endpoints:")
    print("  - POST /runsync     - Run sync handler (giống RunPod)")
    print("  - POST /runasync    - Run async handler (giống RunPod)")
    print("  - POST /text2image  - Text2Image với workflow template")
    print("  - POST /test/sync   - Test sync handler")
    print("  - POST /test/async  - Test async handler")
    print("\n" + "="*60)
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "test_serverless_api:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == "__main__":
    main()
