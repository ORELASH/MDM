"""
FastAPI Server Launcher
Production-ready server configuration with enhanced features.
"""

import os
import sys
import signal
import asyncio
from pathlib import Path
from typing import Optional
import uvicorn
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.logging_system import RedshiftManagerLogger as RedshiftLogger
from api.main import app
# from api.middleware import setup_all_middleware

class APIServer:
    """
    FastAPI server manager with graceful shutdown and monitoring
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8000, workers: int = 1):
        self.host = host
        self.port = port
        self.workers = workers
        self.logger = RedshiftLogger()
        self.server: Optional[uvicorn.Server] = None
        
        # Setup middleware
        # setup_all_middleware(app, self.logger)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.log_action_start(f"Received signal {signum}, initiating graceful shutdown")
        if self.server:
            self.server.should_exit = True
    
    async def start_async(self):
        """Start server asynchronously"""
        config = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            workers=self.workers,
            log_level="info",
            access_log=True,
            reload=False,  # Disable reload in production
            loop="auto"
        )
        
        self.server = uvicorn.Server(config)
        
        self.logger.log_action_start(
            f"Starting FastAPI server on {self.host}:{self.port}",
            {
                "host": self.host,
                "port": self.port,
                "workers": self.workers,
                "docs_url": f"http://{self.host}:{self.port}/docs"
            }
        )
        
        try:
            await self.server.serve()
        except Exception as e:
            self.logger.log_error(f"Server error: {e}")
            raise
        finally:
            self.logger.log_action_end("FastAPI server stopped")
    
    def start(self):
        """Start server synchronously"""
        try:
            asyncio.run(self.start_async())
        except KeyboardInterrupt:
            self.logger.log_action_end("Server stopped by user interrupt")
        except Exception as e:
            self.logger.log_error(f"Failed to start server: {e}")
            raise
    
    def start_dev(self):
        """Start development server with hot reload"""
        self.logger.log_action_start("Starting development server with hot reload")
        
        uvicorn.run(
            "api.main:app",
            host=self.host,
            port=self.port,
            reload=True,
            log_level="debug",
            access_log=True,
            reload_dirs=[str(project_root)]
        )

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RedshiftManager API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    parser.add_argument("--dev", action="store_true", help="Run in development mode")
    
    args = parser.parse_args()
    
    server = APIServer(host=args.host, port=args.port, workers=args.workers)
    
    if args.dev:
        print("🔧 Starting in DEVELOPMENT mode")
        server.start_dev()
    else:
        print("🚀 Starting in PRODUCTION mode")
        server.start()

if __name__ == "__main__":
    main()