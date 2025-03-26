import asyncio
import uvicorn
from uvicorn.config import Config
import sys
import os
import signal

# Add the current directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the backend modules (but don't run their app instances yet)
import backend
import backend_availability

# This class runs a FastAPI app with uvicorn on a specific host and port
class AppRunner:
    def __init__(self, app, host, port):
        self.app = app
        self.host = host
        self.port = port
        self.config = Config(app, host=host, port=port, log_level="info")
        self.server = None
    
    async def start(self):
        self.server = uvicorn.Server(self.config)
        await self.server.serve()
    
    async def stop(self):
        if self.server:
            self.server.should_exit = True

async def run_both_apps():
    # Create tasks for both apps
    backend_runner = AppRunner(
        "backend:app", 
        host="172.16.16.27", 
        port=8000
    )
    
    availability_runner = AppRunner(
        "backend_availability:app", 
        host="172.16.16.27", 
        port=8001
    )

    # Initialize backend's connection pool
    await backend.initialize_connection_pool()
    
    # Start cache cleanup task
    asyncio.create_task(backend.cache_cleanup_task())
    
    # Print startup message
    print("=== MRP Combined Application ===")
    print(f"Backend API running at: http://172.16.16.27:8000")
    print(f"Availability API running at: http://172.16.16.27:8001")
    print("Both applications are running in the same process")
    print("Press CTRL+C to stop all services")
    
    # Create tasks to run both servers
    backend_task = asyncio.create_task(backend_runner.start())
    availability_task = asyncio.create_task(availability_runner.start())
    
    # Wait for both to complete or be cancelled
    done, pending = await asyncio.wait(
        [backend_task, availability_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    
    # Clean up if one finishes/crashes
    for task in pending:
        task.cancel()

def handle_exit(sig, frame):
    print("Shutting down all servers...")
    loop = asyncio.get_event_loop()
    loop.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # Run both applications in the same process
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_both_apps())
    except KeyboardInterrupt:
        print("Manual interruption received")
    finally:
        loop.close()
        print("Shutdown complete") 