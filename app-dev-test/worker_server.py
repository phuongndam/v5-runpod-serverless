#!/usr/bin/env python3
"""
Worker Server để nhận requests từ API Server
và xử lý với ComfyUI
"""

import json
import asyncio
import aiohttp
from aiohttp import web
import logging
import sys
import os

# Thêm ComfyUI vào Python path
sys.path.append('/app/ComfyUI')

# Import worker từ rp_handler
from rp_handler import ComfyUIWorker

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkerServer:
    def __init__(self):
        self.worker = ComfyUIWorker()
        self.initialized = False
        
    async def initialize(self):
        """Khởi tạo worker"""
        if not self.initialized:
            await self.worker.initialize()
            self.initialized = True
            logger.info("Worker initialized successfully")
    
    async def handle_process(self, request):
        """Xử lý POST request để process job"""
        try:
            job_data = await request.json()
            logger.info(f"Processing job: {job_data.get('input', {})}")
            
            # Process job
            result = await self.worker.process_workflow(
                job_data.get('workflow'), 
                job_data.get('input', {})
            )
            
            return web.json_response({
                'success': True,
                'result': result
            })
            
        except Exception as e:
            logger.error(f"Worker error: {e}")
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
        app.router.add_post('/process', self.handle_process)
        app.router.add_get('/health', self.handle_health)
        return app

async def main():
    """Main function"""
    worker_server = WorkerServer()
    
    # Initialize worker
    await worker_server.initialize()
    
    app = worker_server.create_app()
    
    logger.info("Starting Worker Server on port 8001...")
    logger.info("Endpoints:")
    logger.info("  POST /process - Process job")
    logger.info("  GET /health - Health check")
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8001)
    await site.start()
    
    # Keep running
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Worker Server stopped")

if __name__ == "__main__":
    asyncio.run(main())
