"""FM Manager Game Server.

FastAPI-based server supporting multiplayer online gameplay with:
- WebSocket connections for real-time updates
- HTTP API for game management
- LLM agent integration for AI managers
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from fm_manager.server.game_room import GameRoom, RoomStatus, PlayerRole
from fm_manager.engine.llm_client import LLMClient, LLMProvider


# Global state
rooms: Dict[str, GameRoom] = {}
llm_client: Optional[LLMClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Server lifespan management."""
    # Startup
    global llm_client
    llm_client = LLMClient()
    print("🚀 FM Manager Server starting...")
    print(f"   LLM Client initialized")
    yield
    # Shutdown
    print("🛑 Server shutting down...")
    for room in rooms.values():
        await room.close()


app = FastAPI(
    title="FM Manager Server",
    description="Multiplayer football manager game server with LLM support",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HTTP API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Server health check."""
    return {
        "status": "running",
        "version": "0.1.0",
        "active_rooms": len([r for r in rooms.values() if r.status != RoomStatus.CLOSED]),
        "total_rooms": len(rooms)
    }


@app.get("/api/rooms")
async def list_rooms():
    """List all available game rooms."""
    return {
        "rooms": [
            {
                "id": room.room_id,
                "name": room.name,
                "status": room.status.value,
                "player_count": len(room.players),
                "max_players": room.max_players,
                "has_ai": room.has_ai_manager(),
                "created_at": room.created_at.isoformat()
            }
            for room in rooms.values()
            if room.status != RoomStatus.CLOSED
        ]
    }


@app.post("/api/rooms")
async def create_room(
    name: str,
    max_players: int = 4,
    season_length: int = 38,
    enable_ai: bool = True
):
    """Create a new game room."""
    room_id = str(uuid.uuid4())[:8]
    room = GameRoom(
        room_id=room_id,
        name=name,
        max_players=max_players,
        season_length=season_length,
        enable_ai=enable_ai,
        llm_client=llm_client
    )
    rooms[room_id] = room
    
    return {
        "room_id": room_id,
        "name": name,
        "status": room.status.value,
        "join_url": f"/api/rooms/{room_id}/join"
    }


@app.get("/api/rooms/{room_id}")
async def get_room(room_id: str):
    """Get room details."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    return room.to_dict()


@app.post("/api/rooms/{room_id}/join")
async def join_room(room_id: str, player_name: str, role: str = "human"):
    """Join a game room."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    
    if room.status == RoomStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Room is closed")
    
    if len(room.players) >= room.max_players:
        raise HTTPException(status_code=400, detail="Room is full")
    
    player_id = str(uuid.uuid4())[:8]
    player_role = PlayerRole.HUMAN if role == "human" else PlayerRole.LLM
    
    await room.add_player(player_id, player_name, player_role)
    
    return {
        "player_id": player_id,
        "room_id": room_id,
        "role": player_role.value,
        "ws_url": f"/ws/rooms/{room_id}?player_id={player_id}"
    }


@app.post("/api/rooms/{room_id}/start")
async def start_game(room_id: str, player_id: str):
    """Start the game (host only)."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    
    if room.host_id != player_id:
        raise HTTPException(status_code=403, detail="Only host can start the game")
    
    if room.status != RoomStatus.WAITING:
        raise HTTPException(status_code=400, detail="Game already started")
    
    success = await room.start_game()
    
    return {"success": success, "status": room.status.value}


@app.post("/api/rooms/{room_id}/select-club")
async def select_club(room_id: str, player_id: str, club_id: int):
    """Select a club to manage."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    success = await room.select_club(player_id, club_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Club not available")
    
    return {"success": True, "club_id": club_id}


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@app.websocket("/ws/rooms/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_id: Optional[str] = None):
    """WebSocket connection for real-time game updates."""
    if room_id not in rooms:
        await websocket.close(code=4004, reason="Room not found")
        return
    
    room = rooms[room_id]
    
    if not player_id or player_id not in room.players:
        await websocket.close(code=4001, reason="Invalid player")
        return
    
    # Accept connection first
    await websocket.accept()
    
    # Connect to room
    await room.connect_websocket(player_id, websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            msg_type = message.get("type")
            
            if msg_type == "chat":
                await room.broadcast_chat(player_id, message.get("content", ""))
            
            elif msg_type == "decision":
                # Player made a decision (tactics, transfer, etc.)
                await room.handle_player_decision(player_id, message)
            
            elif msg_type == "ready":
                await room.set_player_ready(player_id, message.get("ready", True))
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
    
    except WebSocketDisconnect:
        await room.disconnect_websocket(player_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await room.disconnect_websocket(player_id)


# ============================================================================
# LLM Agent Management
# ============================================================================

@app.post("/api/rooms/{room_id}/add-ai-manager")
async def add_ai_manager(
    room_id: str,
    player_id: str,
    ai_name: str,
    personality: str = "balanced",
    provider: str = "openai",
    model: Optional[str] = None
):
    """Add an LLM-powered AI manager to the room."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    
    if room.host_id != player_id:
        raise HTTPException(status_code=403, detail="Only host can add AI managers")
    
    ai_id = str(uuid.uuid4())[:8]
    
    success = await room.add_ai_manager(
        ai_id=ai_id,
        ai_name=ai_name,
        personality=personality,
        provider=provider,
        model=model
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add AI manager")
    
    return {
        "ai_id": ai_id,
        "name": ai_name,
        "personality": personality,
        "provider": provider
    }


@app.delete("/api/rooms/{room_id}/remove-ai-manager")
async def remove_ai_manager(room_id: str, player_id: str, ai_id: str):
    """Remove an AI manager from the room."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    
    if room.host_id != player_id:
        raise HTTPException(status_code=403, detail="Only host can remove AI managers")
    
    success = await room.remove_ai_manager(ai_id)
    
    return {"success": success}


# ============================================================================
# Background Tasks
# ============================================================================

@app.post("/api/rooms/{room_id}/simulate-matchday")
async def simulate_matchday(room_id: str, player_id: str, background_tasks: BackgroundTasks):
    """Trigger matchday simulation (host only)."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    
    if room.host_id != player_id:
        raise HTTPException(status_code=403, detail="Only host can trigger simulation")
    
    # Run simulation in background
    background_tasks.add_task(room.simulate_matchday)
    
    return {"success": True, "message": "Matchday simulation started"}


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "fm_manager.server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
