#!/usr/bin/env python3
"""
Script to run the FastAPI application locally.
"""
import uvicorn
import os

if __name__ == "__main__":
    # Set default port
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    # Run the FastAPI app
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )

