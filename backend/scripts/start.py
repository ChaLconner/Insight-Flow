#!/usr/bin/env python3
"""
Startup script for the FastAPI backend with proper host binding.
This ensures the server is accessible from the frontend.
"""

import os

import uvicorn
from dotenv import load_dotenv

from utils.logger import app_logger

# Load environment variables
load_dotenv()

app_logger.info("=" * 50)
app_logger.info("STARTING FASTAPI BACKEND SERVER")
app_logger.info("=" * 50)

# Get configuration from environment or use defaults
host = os.getenv("HOST", "0.0.0.0")  # Default to 0.0.0.0 for accessibility
port = int(os.getenv("PORT", "8000"))
reload = os.getenv("RELOAD", "true").lower() == "true"

app_logger.info(f"Host: {host}")
app_logger.info(f"Port: {port}")
app_logger.info(f"Reload: {reload}")
app_logger.info(f"Server will be accessible at: http://{host}:{port}")
app_logger.info("=" * 50)

# Start the server with proper configuration
if __name__ == "__main__":
    uvicorn.run("main:app", host=host, port=port, reload=reload, log_level="info")
