"""
Entrypoint for running the backend server with proper Windows event loop policy.
This is needed for Python 3.13+ on Windows to support Playwright subprocess spawning.
"""
import asyncio
import sys

# Must be set before any asyncio operations
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)