#!/usr/bin/env python3
"""
Start test environment for ComfyUI RunPod integration
"""

import subprocess
import sys
import os
import time
import signal
import threading
from typing import Optional

class TestEnvironment:
    def __init__(self):
        self.api_process: Optional[subprocess.Popen] = None
        self.running = False
        
    def install_dependencies(self):
        """Install required dependencies"""
        print("📦 Installing dependencies...")
        
        try:
            # Install FastAPI and related packages
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "fastapi", "uvicorn", "pydantic", "requests"
            ], check=True)
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
    
    def start_api_server(self):
        """Start the mock API server"""
        print("🌐 Starting API server...")
        
        try:
            self.api_process = subprocess.Popen([
                sys.executable, "runpod_mock_server.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a moment for server to start
            time.sleep(3)
            
            # Check if process is still running
            if self.api_process.poll() is None:
                print("✅ API server started successfully")
                print("   Server running at: http://localhost:8000")
                print("   API docs at: http://localhost:8000/docs")
                return True
            else:
                stdout, stderr = self.api_process.communicate()
                print(f"❌ API server failed to start:")
                print(f"   stdout: {stdout.decode()}")
                print(f"   stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting API server: {e}")
            return False
    
    def run_tests(self):
        """Run all tests"""
        print("\n🧪 Running tests...")
        
        tests = [
            ("Direct Handler Test", "python test_handler_direct.py"),
            ("API Integration Test", "python test_handler_api.py")
        ]
        
        for test_name, command in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = subprocess.run(command, shell=True, cwd=".")
                if result.returncode == 0:
                    print(f"✅ {test_name} passed")
                else:
                    print(f"❌ {test_name} failed")
            except Exception as e:
                print(f"❌ {test_name} error: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        print("\n🧹 Cleaning up...")
        
        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=5)
                print("✅ API server stopped")
            except subprocess.TimeoutExpired:
                self.api_process.kill()
                print("⚠️  API server force killed")
            except Exception as e:
                print(f"⚠️  Error stopping API server: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def run_interactive_mode(self):
        """Run in interactive mode"""
        print("\n🎮 Interactive Mode")
        print("Commands:")
        print("  test - Run all tests")
        print("  api - Test API endpoints manually")
        print("  direct - Test handler directly")
        print("  docker - Test Docker integration")
        print("  quit - Exit")
        
        while self.running:
            try:
                command = input("\n> ").strip().lower()
                
                if command == "quit":
                    break
                elif command == "test":
                    self.run_tests()
                elif command == "api":
                    self.test_api_manually()
                elif command == "direct":
                    subprocess.run([sys.executable, "test_handler_direct.py"])
                elif command == "docker":
                    subprocess.run([sys.executable, "test_docker_integration.py"])
                elif command == "help":
                    print("Available commands: test, api, direct, docker, quit")
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def test_api_manually(self):
        """Test API endpoints manually"""
        print("\n🔧 Manual API Testing")
        print("You can now test the API using curl or any HTTP client:")
        print("\nExample curl commands:")
        print("""
# Health check
curl http://localhost:8000/health

# Generate image (sync)
curl -X POST http://localhost:8000/runsync \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "a beautiful landscape", "width": 1024, "height": 768}'

# Generate image (async)
curl -X POST http://localhost:8000/run \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "a cute cat", "width": 512, "height": 512}'

# Check job status
curl http://localhost:8000/status/JOB_ID

# List all jobs
curl http://localhost:8000/jobs
        """)
    
    def start(self, interactive=True):
        """Start the test environment"""
        print("🚀 Starting ComfyUI RunPod Test Environment")
        print("=" * 50)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.running = True
        
        # Install dependencies
        if not self.install_dependencies():
            return False
        
        # Start API server
        if not self.start_api_server():
            return False
        
        try:
            if interactive:
                self.run_interactive_mode()
            else:
                self.run_tests()
        finally:
            self.cleanup()
        
        return True

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ComfyUI RunPod Test Environment")
    parser.add_argument("--no-interactive", action="store_true", 
                       help="Run tests and exit (no interactive mode)")
    parser.add_argument("--test-only", action="store_true",
                       help="Run tests only (don't start API server)")
    
    args = parser.parse_args()
    
    env = TestEnvironment()
    
    if args.test_only:
        env.run_tests()
    else:
        env.start(interactive=not args.no_interactive)

if __name__ == "__main__":
    main()
