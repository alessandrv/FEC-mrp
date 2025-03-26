# MRP Combined Application

This application runs both backend.py and backend_availability.py FastAPI applications in the same process but preserves their separate ports to maintain security boundaries.

## Running the Combined Application

To run the combined application, use the following command:

```bash
python main.py
```

This will start:
- The backend API on port 8000 (http://172.16.16.27:8000)
- The availability API on port 8001 (http://172.16.16.27:8001)

Both will run in a single Python process, reducing overall CPU usage.

## How It Works

Unlike a traditional combined FastAPI application where APIs are mounted under different paths, this solution:

1. Runs both FastAPI applications in their original form
2. Uses asyncio to run both uvicorn servers in the same process
3. Maintains the original port separation for security purposes
4. Shares resources like the connection pool where possible

## Benefits

1. **Reduced CPU Usage**: Running in a single process instead of two separate processes
2. **Maintained Security**: Preserves the original port separation (8001 remains externally exposed)
3. **No URL Changes Required**: All existing endpoints work with their original URLs
4. **Shared Resources**: Both applications can share common resources and connection pools
5. **Simple Administration**: Both applications start and stop together

## Frontend Applications

No changes to frontend applications are required! All URLs remain the same:

- Backend endpoints: `http://172.16.16.27:8000/...`
- Availability endpoints: `http://172.16.16.27:8001/...`

## Troubleshooting

If you encounter any issues:

1. Make sure both backend.py and backend_availability.py are in the same directory as main.py
2. Check that the correct Python executable is being used in run_server.bat
3. Verify that no other process is already using port 8000 or 8001
4. Look for any import errors in the console output

## Reverting to Separate Processes

If needed, you can still run both applications separately using the original commands:

```bash
python -m uvicorn backend:app --host 172.16.16.27 --reload --port 8000
python -m uvicorn backend_availability:app --host 172.16.16.27 --reload --port 8001
```
