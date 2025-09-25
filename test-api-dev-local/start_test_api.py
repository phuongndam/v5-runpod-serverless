#!/usr/bin/env python3
"""
Script để start test API server
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Start test API server"""
    
    # Đảm bảo đang ở đúng directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("🚀 Starting ComfyUI Test API Server...")
    print(f"📁 Working directory: {os.getcwd()}")
    
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
    print("🌐 Starting server on http://localhost:8000")
    print("📖 API docs available at http://localhost:8000/docs")
    print("🔍 Health check at http://localhost:8000/health")
    print("\n" + "="*50)
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "test_api_server:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == "__main__":
    main()
