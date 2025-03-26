# MRP Combined Application

This application combines the backend.py and backend_availability.py FastAPI applications into a single instance to reduce CPU usage and simplify deployment.

## Running the Combined Application

To run the combined application, use the following command:

```bash
python -m uvicorn main:app --host 172.16.16.27 --port 8000 --reload
```

Alternatively, you can execute the main.py file directly:

```bash
python main.py
```

## API Endpoints

The combined application mounts both APIs under different prefixes:

- Original backend.py endpoints are available at `/api/...`
- Original backend_availability.py endpoints are available at `/availability/...`

### Example URL Changes

Before:
- `http://172.16.16.27:8000/articles`
- `http://172.16.16.27:8001/article_history`

After:
- `http://172.16.16.27:8000/api/articles`
- `http://172.16.16.27:8000/availability/article_history`

## Benefits

1. **Reduced CPU Usage**: Running a single uvicorn process instead of two
2. **Simplified Deployment**: Only one service to manage
3. **Common Connection Pool**: Both applications can share the same database connection pool
4. **Easier Maintenance**: All code runs together for easier debugging

## Updating the Frontend

If you have frontend applications that connect to these APIs, you'll need to update the URLs to include the new prefixes.

Example changes:
- From: `fetch('http://172.16.16.27:8000/articles')`
- To: `fetch('http://172.16.16.27:8000/api/articles')`

- From: `fetch('http://172.16.16.27:8001/article_history')`
- To: `fetch('http://172.16.16.27:8000/availability/article_history')`

## Troubleshooting

If you encounter any issues:

1. Make sure both backend.py and backend_availability.py are in the same directory as main.py
2. Check for any endpoint naming conflicts between the two applications
3. Verify that frontend applications have been updated to use the new URL prefixes
