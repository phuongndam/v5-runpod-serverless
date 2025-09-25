#!/usr/bin/env python3
"""
API Server để nhận curl requests từ Windows host
và gửi đến ComfyUI Worker
"""

import json
import asyncio
import aiohttp
from aiohttp import web
import os
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComfyUIAPIServer:
    def __init__(self):
        self.worker_url = "http://localhost:8001"  # Worker sẽ chạy trên port 8001
        self.workflow_path = "/workflow-data/text2image-nunchaku-flux.1-dev.json"
        
    async def handle_generate(self, request):
        """Xử lý POST request để generate image"""
        try:
            data = await request.json()
            prompt = data.get('prompt', '')
            width = data.get('w', 1024)
            height = data.get('h', 1024)
            
            logger.info(f"Received request: prompt='{prompt}', size={width}x{height}")
            
            # Load workflow template
            if not os.path.exists(self.workflow_path):
                return web.json_response({
                    'success': False, 
                    'error': f'Workflow not found: {self.workflow_path}'
                }, status=404)
            
            with open(self.workflow_path, 'r') as f:
                workflow = json.load(f)
            
            # Prepare job data for worker
            job_data = {
                'workflow': workflow,
                'input': {
                    'prompt': prompt,
                    'w': width,
                    'h': height
                }
            }
            
            # Send to worker
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.worker_url}/process", 
                    json=job_data
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return web.json_response(result)
                    else:
                        error_text = await resp.text()
                        return web.json_response({
                            'success': False, 
                            'error': f'Worker error: {error_text}'
                        }, status=500)
                        
        except Exception as e:
            logger.error(f"API error: {e}")
            return web.json_response({
                'success': False, 
                'error': str(e)
            }, status=500)
    
    async def handle_health(self, request):
        """Health check endpoint"""
        return web.json_response({'status': 'healthy'})
    
    def create_app(self):
        """Tạo web application"""
        app = web.Application()
        app.router.add_post('/generate', self.handle_generate)
        app.router.add_get('/health', self.handle_health)
        return app

async def main():
    """Main function"""
    server = ComfyUIAPIServer()
    app = server.create_app()
    
    logger.info("Starting API Server on port 8000...")
    logger.info("Endpoints:")
    logger.info("  POST /generate - Generate image")
    logger.info("  GET /health - Health check")
    logger.info("Example curl:")
    logger.info('  curl -X POST http://localhost:8000/generate -H "Content-Type: application/json" -d \'{"prompt": "a beautiful landscape", "w": 1024, "h": 768}\'')
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    
    # Keep running
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("API Server stopped")

if __name__ == "__main__":
    asyncio.run(main())
