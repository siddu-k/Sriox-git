import uvicorn

if __name__ == "__main__":
    # Run the FastAPI application using Uvicorn
    # Host with 0.0.0.0 to allow connections from any IP
    # Use port 8000 by default
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)