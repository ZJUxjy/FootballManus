"""Game Room Management.

Manages a single game room including:
- Player connections (human and AI)
- Game state management
- WebSocket broadcasting
- Match simulation coordination
"""

import asyncio
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from fastapi import WebSocket

from fm_manager.data.cleaned_data_loader import load_for_match_engine, ClubDataFull
from fm_manager.engine.match_engine_markov import MarkovMatchEngine

# AI Manager personality types
class AIPersonality(Enum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    DEFENSIVE = "defensive"
    TIKI_TAKA = "tiki_taka"
    LONG_BALL = "long_ball"
    YOUTH_FOCUS = "youth_focus"
    MONEYBALL = "moneyball"
    SUPERSTAR = "superstar"
    LLM_POWERED = "llm_powered"


class RoomStatus(Enum):
    """Room lifecycle states."""
    WAITING = "waiting"      # Waiting for players
    SETUP = "setup"          # Club selection phase
    READY = "ready"          # All ready, can start
    PLAYING = "playing"      # Game in progress
    PAUSED = "paused"        # Game paused
    FINISHED = "finished"    # Season completed
    CLOSED = "closed"        # Room closed


class PlayerRole(Enum):
    """Player role types."""
    HUMAN = "human"
    LLM = "llm"
    SPECTATOR = "spectator"


@dataclass
class Player:
    """Player in the game room."""
    player_id: str
    name: str
    role: PlayerRole
    club_id: Optional[int] = None
    is_ready: bool = False
    is_connected: bool = False
    websocket: Optional[WebSocket] = None
    
    # For AI players
    ai_personality: Optional[AIPersonality] = None
    ai_config: Optional[Dict] = None


@dataclass
class MatchResult:
    """Result of a simulated match."""
    home_club_id: int
    away_club_id: int
    home_score: int
    away_score: int
    events: List[Dict] = field(default_factory=list)
    played_at: datetime = field(default_factory=datetime.now)


class GameRoom:
    """A game room managing a multiplayer session."""
    
    def __init__(
        self,
        room_id: str,
        name: str,
        max_players: int = 4,
        season_length: int = 38,
        enable_ai: bool = True,
        llm_client=None
    ):
        self.room_id = room_id
        self.name = name
        self.max_players = max_players
        self.season_length = season_length
        self.enable_ai = enable_ai
        self.llm_client = llm_client
        
        self.status = RoomStatus.WAITING
        self.created_at = datetime.now()
        self.host_id: Optional[str] = None
        
        # Players and clubs
        self.players: Dict[str, Player] = {}
        self.available_clubs: List[ClubDataFull] = []
        self.selected_clubs: Dict[str, int] = {}  # player_id -> club_id
        
        # Game state
        self.current_matchday = 0
        self.match_results: List[MatchResult] = []
        self.standings: Dict[int, Dict] = {}  # club_id -> stats
        
        # Match engine
        self.match_engine = MarkovMatchEngine()
        
        # Load data
        self._load_data()
    
    def _load_data(self):
        """Load club data."""
        try:
            clubs, _ = load_for_match_engine()
            # Filter to major leagues for now
            major_leagues = ["England Premier League"]
            self.available_clubs = [
                c for c in clubs.values() 
                if c.league in major_leagues
            ]
            print(f"Loaded {len(self.available_clubs)} clubs for room {self.room_id}")
        except Exception as e:
            print(f"Error loading clubs: {e}")
            self.available_clubs = []
    
    # ========================================================================
    # Player Management
    # ========================================================================
    
    async def add_player(self, player_id: str, name: str, role: PlayerRole) -> bool:
        """Add a player to the room."""
        if len(self.players) >= self.max_players:
            return False
        
        if player_id in self.players:
            return False
        
        player = Player(
            player_id=player_id,
            name=name,
            role=role,
            is_connected=False
        )
        
        self.players[player_id] = player
        
        # First player becomes host
        if self.host_id is None:
            self.host_id = player_id
        
        await self._broadcast_system_message(f"{name} joined the room")
        
        return True
    
    async def remove_player(self, player_id: str) -> bool:
        """Remove a player from the room."""
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        await self._broadcast_system_message(f"{player.name} left the room")
        
        # Release club if selected
        if player_id in self.selected_clubs:
            del self.selected_clubs[player_id]
        
        del self.players[player_id]
        
        # Transfer host if needed
        if player_id == self.host_id and self.players:
            self.host_id = next(iter(self.players.keys()))
            new_host = self.players[self.host_id]
            await self._broadcast_system_message(f"{new_host.name} is now the host")
        
        return True
    
    async def add_ai_manager(
        self,
        ai_id: str,
        ai_name: str,
        personality: str = "balanced",
        provider: str = "openai",
        model: Optional[str] = None
    ) -> bool:
        """Add an LLM-powered AI manager."""
        if not self.enable_ai or not self.llm_client:
            return False
        
        if len(self.players) >= self.max_players:
            return False
        
        # Create AI player
        try:
            # Map personality string to enum
            personality_map = {
                "aggressive": AIPersonality.AGGRESSIVE,
                "balanced": AIPersonality.BALANCED,
                "defensive": AIPersonality.DEFENSIVE,
                "tiki_taka": AIPersonality.TIKI_TAKA,
                "long_ball": AIPersonality.LONG_BALL,
                "youth_focus": AIPersonality.YOUTH_FOCUS,
                "moneyball": AIPersonality.MONEYBALL,
                "superstar": AIPersonality.SUPERSTAR,
                "llm_powered": AIPersonality.LLM_POWERED,
            }
            ai_personality = personality_map.get(personality.lower(), AIPersonality.BALANCED)
            
            player = Player(
                player_id=ai_id,
                name=ai_name,
                role=PlayerRole.LLM,
                ai_personality=ai_personality,
                ai_config={
                    "personality": personality,
                    "provider": provider,
                    "model": model
                }
            )
            
            self.players[ai_id] = player
            
            await self._broadcast_system_message(
                f"AI Manager '{ai_name}' ({personality}) joined"
            )
            
            return True
            
        except Exception as e:
            print(f"Error creating AI manager: {e}")
            return False
    
    async def remove_ai_manager(self, ai_id: str) -> bool:
        """Remove an AI manager."""
        if ai_id not in self.players:
            return False
        
        player = self.players[ai_id]
        if player.role != PlayerRole.LLM:
            return False
        
        return await self.remove_player(ai_id)
    
    def has_ai_manager(self) -> bool:
        """Check if room has any AI managers."""
        return any(p.role == PlayerRole.LLM for p in self.players.values())
    
    # ========================================================================
    # WebSocket Management
    # ========================================================================
    
    async def connect_websocket(self, player_id: str, websocket: WebSocket):
        """Connect a player's WebSocket."""
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        player.websocket = websocket
        player.is_connected = True
        
        await websocket.send_json({
            "type": "connected",
            "player_id": player_id,
            "room_id": self.room_id,
            "status": self.status.value,
            "players": [
                {
                    "id": p.player_id,
                    "name": p.name,
                    "role": p.role.value,
                    "club_id": p.club_id,
                    "is_ready": p.is_ready
                }
                for p in self.players.values()
            ]
        })
        
        await self._broadcast_player_list()
        return True
    
    async def disconnect_websocket(self, player_id: str):
        """Disconnect a player's WebSocket."""
        if player_id not in self.players:
            return
        
        player = self.players[player_id]
        player.is_connected = False
        player.websocket = None
        
        await self._broadcast_player_list()
    
    # ========================================================================
    # Game State Management
    # ========================================================================
    
    async def select_club(self, player_id: str, club_id: int) -> bool:
        """Select a club for a player."""
        if player_id not in self.players:
            return False
        
        # Check if club is available
        if club_id in self.selected_clubs.values():
            return False
        
        club = next((c for c in self.available_clubs if c.id == club_id), None)
        if not club:
            return False
        
        player = self.players[player_id]
        player.club_id = club_id
        self.selected_clubs[player_id] = club_id
        
        await self._broadcast({
            "type": "club_selected",
            "player_id": player_id,
            "club_id": club_id,
            "club_name": club.name
        })
        
        # Check if all players have clubs
        if len(self.selected_clubs) == len(self.players):
            self.status = RoomStatus.READY
        
        return True
    
    async def set_player_ready(self, player_id: str, ready: bool = True):
        """Set player's ready status."""
        if player_id not in self.players:
            return
        
        self.players[player_id].is_ready = ready
        await self._broadcast_player_list()
    
    async def start_game(self) -> bool:
        """Start the game."""
        if self.status not in [RoomStatus.WAITING, RoomStatus.READY]:
            return False
        
        # Check if all players have clubs
        if len(self.selected_clubs) != len(self.players):
            return False
        
        self.status = RoomStatus.PLAYING
        self.current_matchday = 1
        
        # Initialize standings
        for player in self.players.values():
            if player.club_id:
                self.standings[player.club_id] = {
                    "club_id": player.club_id,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "gf": 0,
                    "ga": 0,
                    "gd": 0,
                    "points": 0
                }
        
        await self._broadcast({
            "type": "game_started",
            "matchday": 1,
            "season_length": self.season_length
        })
        
        return True
    
    # ========================================================================
    # Match Simulation
    # ========================================================================
    
    async def simulate_matchday(self):
        """Simulate one matchday."""
        if self.status != RoomStatus.PLAYING:
            return
        
        await self._broadcast({
            "type": "matchday_start",
            "matchday": self.current_matchday
        })
        
        # Get all clubs
        clubs = list(self.selected_clubs.values())
        if len(clubs) < 2:
            return
        
        # Simple round-robin pairing
        random.shuffle(clubs)
        matches = []
        
        for i in range(0, len(clubs) - 1, 2):
            if i + 1 < len(clubs):
                home_club_id = clubs[i]
                away_club_id = clubs[i + 1]
                
                result = await self._simulate_match(home_club_id, away_club_id)
                matches.append(result)
                
                # Update standings
                self._update_standings(result)
                
                # Broadcast result
                await self._broadcast({
                    "type": "match_result",
                    "match": {
                        "home_club_id": result.home_club_id,
                        "away_club_id": result.away_club_id,
                        "home_score": result.home_score,
                        "away_score": result.away_score,
                        "home_club_name": self._get_club_name(result.home_club_id),
                        "away_club_name": self._get_club_name(result.away_club_id)
                    }
                })
                
                # Small delay for drama
                await asyncio.sleep(0.5)
        
        self.match_results.extend(matches)
        self.current_matchday += 1
        
        # Check season end
        if self.current_matchday > self.season_length:
            self.status = RoomStatus.FINISHED
            await self._broadcast({
                "type": "season_finished",
                "final_standings": self._get_sorted_standings()
            })
        else:
            await self._broadcast({
                "type": "matchday_complete",
                "matchday": self.current_matchday - 1,
                "standings": self._get_sorted_standings()
            })
    
    async def _simulate_match(self, home_club_id: int, away_club_id: int) -> MatchResult:
        """Simulate a single match."""
        # Get clubs
        home_club = next((c for c in self.available_clubs if c.id == home_club_id), None)
        away_club = next((c for c in self.available_clubs if c.id == away_club_id), None)
        
        if not home_club or not away_club:
            return MatchResult(home_club_id, away_club_id, 0, 0)
        
        # Build lineups
        from fm_manager.engine.match_engine_adapter import ClubSquadBuilder
        
        home_builder = ClubSquadBuilder(home_club)
        away_builder = ClubSquadBuilder(away_club)
        
        home_lineup = home_builder.build_lineup("4-3-3")
        away_lineup = away_builder.build_lineup("4-3-3")
        
        # Simulate
        match_state = self.match_engine.simulate(home_lineup, away_lineup)
        
        return MatchResult(
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            home_score=match_state.home_score,
            away_score=match_state.away_score,
            events=[
                {
                    "minute": e.minute,
                    "type": e.event_type.name,
                    "description": e.description
                }
                for e in match_state.events if "GOAL" in e.event_type.name
            ]
        )
    
    def _update_standings(self, result: MatchResult):
        """Update league standings."""
        home = self.standings.get(result.home_club_id)
        away = self.standings.get(result.away_club_id)
        
        if not home or not away:
            return
        
        home["played"] += 1
        away["played"] += 1
        home["gf"] += result.home_score
        home["ga"] += result.away_score
        away["gf"] += result.away_score
        away["ga"] += result.home_score
        
        if result.home_score > result.away_score:
            home["won"] += 1
            home["points"] += 3
            away["lost"] += 1
        elif result.home_score < result.away_score:
            away["won"] += 1
            away["points"] += 3
            home["lost"] += 1
        else:
            home["drawn"] += 1
            away["drawn"] += 1
            home["points"] += 1
            away["points"] += 1
        
        home["gd"] = home["gf"] - home["ga"]
        away["gd"] = away["gf"] - away["ga"]
    
    def _get_club_name(self, club_id: int) -> str:
        """Get club name by ID."""
        club = next((c for c in self.available_clubs if c.id == club_id), None)
        return club.name if club else f"Club {club_id}"
    
    def _get_sorted_standings(self) -> List[Dict]:
        """Get sorted standings."""
        standings = list(self.standings.values())
        standings.sort(key=lambda x: (-x["points"], -x["gd"], -x["gf"]))
        
        for i, s in enumerate(standings, 1):
            s["position"] = i
            s["club_name"] = self._get_club_name(s["club_id"])
        
        return standings
    
    # ========================================================================
    # Broadcasting
    # ========================================================================
    
    async def _broadcast(self, message: dict):
        """Broadcast message to all connected players."""
        for player in self.players.values():
            if player.is_connected and player.websocket:
                try:
                    await player.websocket.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to {player.name}: {e}")
    
    async def _broadcast_system_message(self, content: str):
        """Broadcast a system message."""
        await self._broadcast({
            "type": "system",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _broadcast_player_list(self):
        """Broadcast updated player list."""
        await self._broadcast({
            "type": "player_list",
            "players": [
                {
                    "id": p.player_id,
                    "name": p.name,
                    "role": p.role.value,
                    "club_id": p.club_id,
                    "is_ready": p.is_ready,
                    "is_connected": p.is_connected
                }
                for p in self.players.values()
            ]
        })
    
    async def broadcast_chat(self, player_id: str, content: str):
        """Broadcast chat message."""
        if player_id not in self.players:
            return
        
        player = self.players[player_id]
        await self._broadcast({
            "type": "chat",
            "player_id": player_id,
            "player_name": player.name,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    # ========================================================================
    # Message Handlers
    # ========================================================================
    
    async def handle_player_decision(self, player_id: str, message: dict):
        """Handle a player decision."""
        # TODO: Implement decision handling (tactics, transfers, etc.)
        await self._broadcast({
            "type": "decision_received",
            "player_id": player_id,
            "decision_type": message.get("decision_type"),
            "timestamp": datetime.now().isoformat()
        })
    
    # ========================================================================
    # Cleanup
    # ========================================================================
    
    async def close(self):
        """Close the room."""
        self.status = RoomStatus.CLOSED
        
        for player in self.players.values():
            if player.websocket:
                try:
                    await player.websocket.close()
                except:
                    pass
    
    # ========================================================================
    # Serialization
    # ========================================================================
    
    def to_dict(self) -> dict:
        """Convert room to dictionary."""
        return {
            "room_id": self.room_id,
            "name": self.name,
            "host_id": self.host_id,
            "status": self.status.value,
            "max_players": self.max_players,
            "current_matchday": self.current_matchday,
            "season_length": self.season_length,
            "players": [
                {
                    "id": p.player_id,
                    "name": p.name,
                    "role": p.role.value,
                    "club_id": p.club_id,
                    "is_ready": p.is_ready
                }
                for p in self.players.values()
            ],
            "available_clubs": [
                {"id": c.id, "name": c.name, "league": c.league}
                for c in self.available_clubs[:20]  # Limit for performance
            ],
            "standings": self._get_sorted_standings() if self.standings else []
        }
