# Multiplayer System Documentation

## Overview

FM Manager now supports multiplayer online gameplay with WebSocket-based real-time communication. Players can join game rooms, manage clubs, and compete against each other (or AI managers) in simulated football seasons.

## Architecture

```
┌─────────────┐      WebSocket       ┌─────────────┐
│   Client 1  │◄────────────────────►│             │
│   (Human)   │                      │   Server    │
└─────────────┘                      │   (FastAPI) │
                                     │             │
┌─────────────┐      WebSocket       │  ┌───────┐  │
│   Client 2  │◄────────────────────►│  │ Rooms │  │
│   (Human)   │                      │  └───┬───┘  │
└─────────────┘                      │      │      │
                                     │  ┌───▼───┐  │
┌─────────────┐      WebSocket       │  │ Match │  │
│   Client 3  │◄────────────────────►│  │Engine │  │
│   (AI/LLM)  │                      │  └───────┘  │
└─────────────┘                      └─────────────┘
```

## Components

### Server (`fm_manager/server/`)

- **`main.py`** - FastAPI application with HTTP and WebSocket endpoints
- **`game_room.py`** - Room management, player connections, game state

### Client (`fm_manager/cli/`)

- **`client.py`** - WebSocket client for server communication
- **`main.py`** - Rich-based CLI interface

## Quick Start

### 1. Start the Server

```bash
python scripts/start_server.py
```

Server will start on:
- HTTP API: http://localhost:8000
- WebSocket: ws://localhost:8000/ws/rooms/{room_id}
- API Docs: http://localhost:8000/docs

### 2. Run the CLI Client

```bash
python -m fm_manager.cli.main
```

Or use the console script:
```bash
fm-cli
```

### 3. Create a Game Room

In the CLI:
```
> create
Room name: My Game
Max players: 4
Enable AI managers? [y/n]: y
✓ Room created: abc123
```

### 4. Join and Play

```
> join
Room ID: abc123
Your name: Player1
✓ Joined as: xyz789
```

## HTTP API Endpoints

### Room Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rooms` | List all rooms |
| POST | `/api/rooms` | Create new room |
| GET | `/api/rooms/{id}` | Get room details |
| POST | `/api/rooms/{id}/join` | Join a room |
| POST | `/api/rooms/{id}/start` | Start game |
| POST | `/api/rooms/{id}/select-club` | Select club |
| POST | `/api/rooms/{id}/simulate-matchday` | Simulate matchday |

### AI Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rooms/{id}/add-ai-manager` | Add AI player |
| DELETE | `/api/rooms/{id}/remove-ai-manager` | Remove AI player |

## WebSocket Protocol

### Client → Server Messages

```json
// Chat message
{"type": "chat", "content": "Hello!"}

// Ready status
{"type": "ready", "ready": true}

// Game decision
{"type": "decision", "decision_type": "tactics", "data": {...}}

// Ping
{"type": "ping"}
```

### Server → Client Messages

```json
// Connected confirmation
{"type": "connected", "player_id": "...", "room_id": "..."}

// System message
{"type": "system", "content": "Game started!"}

// Chat message
{"type": "chat", "player_name": "Player1", "content": "Hello!"}

// Match result
{"type": "match_result", "match": {...}}

// Standings update
{"type": "matchday_complete", "standings": [...]}
```

## AI Manager Integration

AI managers can be added to rooms and will:
1. Make tactical decisions based on personality
2. Participate in transfer negotiations
3. Respond to game events

### AI Personalities

- `balanced` - Standard approach
- `aggressive` - Risk-taking, high pressing
- `defensive` - Conservative, counter-attacking
- `tiki_taka` - Possession-based
- `long_ball` - Direct play
- `youth_focus` - Prioritizes young players
- `moneyball` - Data-driven, value-focused
- `superstar` - Wants star players
- `llm_powered` - Uses LLM for complex decisions

### Adding AI via API

```bash
curl -X POST "http://localhost:8000/api/rooms/{room_id}/add-ai-manager" \
  -d "player_id={host_id}" \
  -d "ai_name=AI Manager" \
  -d "personality=balanced" \
  -d "provider=openai"
```

## Testing

Run the multiplayer test:

```bash
python scripts/test_multiplayer.py
```

This will:
1. Create a room
2. Join as human player
3. Add AI manager
4. Select clubs
5. Start game
6. Simulate 3 matchdays

## Game Flow

```
1. CREATE ROOM
   Host creates room with settings
   
2. JOIN ROOM
   Players join via room ID
   AI managers can be added
   
3. SELECT CLUBS
   Each player chooses a club
   
4. START GAME
   Host starts the game
   
5. PLAY SEASON
   Matchdays are simulated
   Real-time updates via WebSocket
   
6. SEASON END
   Final standings
   Awards ceremony
```

## Implementation Notes

### Match Simulation

- Uses `MarkovMatchEngine` for minute-by-minute simulation
- Matches run server-side
- Results broadcast to all connected clients

### State Synchronization

- Game state maintained on server
- WebSocket broadcasts updates
- Clients render UI based on state

### Scalability Considerations

- Currently supports in-memory rooms
- For production, consider:
  - Redis for state persistence
  - Database for match history
  - Load balancing for multiple server instances

## Future Enhancements

- [ ] Spectator mode
- [ ] Replay system
- [ ] Advanced AI with LLM reasoning
- [ ] Tournament brackets (cup competitions)
- [ ] Live match viewing with commentary
