"""WebSocket Client for FM Manager.

Handles connection to game server and real-time communication.
"""

import asyncio
import json
import threading
import time
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed


class GameClient:
    """Client for connecting to FM Manager game server."""
    
    def __init__(self, server_url: str = "ws://localhost:8000"):
        self.server_url = server_url
        self.http_url = server_url.replace("ws://", "http://").replace("wss://", "https://")
        
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.player_id: Optional[str] = None
        self.room_id: Optional[str] = None
        self.player_name: Optional[str] = None
        
        self.connected = False
        self.running = False
        
        # Event handlers
        self._handlers: dict[str, list[Callable]] = {
            "connected": [],
            "disconnected": [],
            "message": [],
            "error": [],
            "match_result": [],
            "chat": [],
            "system": []
        }
        
        self._receive_task: Optional[asyncio.Task] = None
    
    # ========================================================================
    # Event Handlers
    # ========================================================================
    
    def on(self, event: str, handler: Callable):
        """Register an event handler."""
        if event in self._handlers:
            self._handlers[event].append(handler)
    
    def off(self, event: str, handler: Callable):
        """Unregister an event handler."""
        if event in self._handlers and handler in self._handlers[event]:
            self._handlers[event].remove(handler)
    
    def _emit(self, event: str, *args, **kwargs):
        """Emit an event to all handlers."""
        for handler in self._handlers.get(event, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                print(f"Error in {event} handler: {e}")
    
    # ========================================================================
    # Connection Management
    # ========================================================================
    
    async def connect(self, room_id: str, player_id: str) -> bool:
        """Connect to a game room via WebSocket."""
        self.room_id = room_id
        self.player_id = player_id
        
        ws_url = f"{self.server_url}/ws/rooms/{room_id}?player_id={player_id}"
        
        try:
            self.websocket = await websockets.connect(ws_url)
            self.connected = True
            self.running = True
            
            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            self._emit("connected")
            return True
            
        except Exception as e:
            self._emit("error", f"Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from server."""
        self.running = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.connected = False
        self._emit("disconnected")
    
    async def _receive_loop(self):
        """Main receive loop."""
        while self.running and self.websocket:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Emit message event
                self._emit("message", data)
                
                # Emit specific events
                msg_type = data.get("type")
                if msg_type in self._handlers:
                    self._emit(msg_type, data)
                
            except ConnectionClosed:
                self._emit("disconnected")
                break
            except Exception as e:
                self._emit("error", f"Receive error: {e}")
    
    # ========================================================================
    # Message Sending
    # ========================================================================
    
    async def send(self, data: dict) -> bool:
        """Send a message to server."""
        if not self.websocket or not self.connected:
            return False
        
        try:
            await self.websocket.send(json.dumps(data))
            return True
        except Exception as e:
            self._emit("error", f"Send failed: {e}")
            return False
    
    async def send_chat(self, content: str):
        """Send a chat message."""
        return await self.send({
            "type": "chat",
            "content": content
        })
    
    async def send_decision(self, decision_type: str, data: dict):
        """Send a game decision."""
        return await self.send({
            "type": "decision",
            "decision_type": decision_type,
            **data
        })
    
    async def set_ready(self, ready: bool = True):
        """Set ready status."""
        return await self.send({
            "type": "ready",
            "ready": ready
        })
    
    async def ping(self):
        """Send ping."""
        return await self.send({"type": "ping"})
    
    # ========================================================================
    # HTTP API Helpers
    # ========================================================================
    
    async def list_rooms(self) -> list:
        """List available rooms."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.http_url}/api/rooms") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("rooms", [])
                return []
    
    async def get_room_info(self) -> Optional[dict]:
        """Get current room info."""
        import aiohttp
        
        if not self.room_id:
            return None
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.http_url}/api/rooms/{self.room_id}") as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    
    async def create_room(
        self,
        name: str,
        max_players: int = 4,
        enable_ai: bool = True
    ) -> Optional[dict]:
        """Create a new game room."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.http_url}/api/rooms",
                params={"name": name, "max_players": str(max_players), "enable_ai": str(enable_ai).lower()}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    
    async def join_room(self, room_id: str, player_name: str) -> Optional[dict]:
        """Join a game room."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.http_url}/api/rooms/{room_id}/join",
                params={"player_name": player_name}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.player_id = data.get("player_id")
                    self.player_name = player_name
                    self.room_id = room_id
                    return data
                return None
    
    async def select_club(self, club_id: int) -> bool:
        """Select a club."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.http_url}/api/rooms/{self.room_id}/select-club",
                params={"player_id": self.player_id, "club_id": club_id}
            ) as resp:
                return resp.status == 200
    
    async def start_game(self) -> bool:
        """Start the game (host only)."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.http_url}/api/rooms/{self.room_id}/start",
                params={"player_id": self.player_id}
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"[Debug] Start game failed: {resp.status} - {text}")
                return resp.status == 200
    
    async def simulate_matchday(self) -> bool:
        """Trigger matchday simulation (host only)."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.http_url}/api/rooms/{self.room_id}/simulate-matchday",
                params={"player_id": self.player_id}
            ) as resp:
                return resp.status == 200
