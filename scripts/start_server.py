#!/usr/bin/env python3
"""Start the FM Manager game server."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fm_manager.server.main import app
import uvicorn

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   FM Manager Game Server                                 ║
    ║                                                          ║
    ║   WebSocket: ws://localhost:8000/ws/rooms/{room_id}     ║
    ║   HTTP API:  http://localhost:8000/api/                 ║
    ║   Docs:      http://localhost:8000/docs                 ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "fm_manager.server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
