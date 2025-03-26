import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add the current directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the apps
from backend import app as backend_app
from backend_availability import app as availability_app
from backend import initialize_connection_pool, cache_cleanup_task

# Create a new FastAPI application to host both apps
app = FastAPI(title="MRP Combined API")

# Configure CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the backend app at /api
app.mount("/api", backend_app)

# Mount the availability app at /availability
app.mount("/availability", availability_app)

# Add a root endpoint
@app.get("/")
async def root():
    return {
        "message": "MRP Combined API",
        "endpoints": {
            "backend": "/api/...",
            "availability": "/availability/..."
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    # Initialize the connection pool from backend.py
    await initialize_connection_pool()
    
    # Start the cache cleanup task in the background
    asyncio.create_task(cache_cleanup_task())
    
    print("MRP Combined API started successfully")

# If executed directly, run the combined app
if __name__ == "__main__":
    import uvicorn
    
    # Run with the same settings as the original command
    uvicorn.run(
        "main:app", 
        host="172.16.16.27", 
        port=8000, 
        reload=True
    ) 