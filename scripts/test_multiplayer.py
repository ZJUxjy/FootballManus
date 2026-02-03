#!/usr/bin/env python3
"""Test multiplayer functionality.

This script tests the game server by:
1. Creating a room
2. Adding a human player
3. Adding an AI manager
4. Selecting clubs
5. Starting the game
6. Simulating a few matchdays
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp


SERVER_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


async def test_multiplayer():
    """Test multiplayer flow."""
    print("=" * 60)
    print("FM Manager Multiplayer Test")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 1. Check server health
        print("\n1. Checking server health...")
        async with session.get(f"{SERVER_URL}/") as resp:
            if resp.status != 200:
                print("❌ Server not running!")
                print("   Start server with: python scripts/start_server.py")
                return
            data = await resp.json()
            print(f"✅ Server running (v{data.get('version', '?')})")
        
        # 2. Create a room
        print("\n2. Creating game room...")
        async with session.post(
            f"{SERVER_URL}/api/rooms",
            params={"name": "Test Room", "max_players": 4, "enable_ai": True}
        ) as resp:
            if resp.status != 200:
                print(f"❌ Failed to create room: {resp.status}")
                return
            room_data = await resp.json()
            room_id = room_data["room_id"]
            print(f"✅ Room created: {room_id}")
        
        # 3. Join as human player
        print("\n3. Joining as human player...")
        async with session.post(
            f"{SERVER_URL}/api/rooms/{room_id}/join",
            params={"player_name": "TestPlayer", "role": "human"}
        ) as resp:
            if resp.status != 200:
                print(f"❌ Failed to join: {resp.status}")
                return
            player_data = await resp.json()
            player_id = player_data["player_id"]
            print(f"✅ Joined as: {player_id}")
        
        # 4. Add AI manager
        print("\n4. Adding AI manager...")
        async with session.post(
            f"{SERVER_URL}/api/rooms/{room_id}/add-ai-manager",
            params={
                "player_id": player_id,
                "ai_name": "AI Manager",
                "personality": "balanced",
                "provider": "mock"
            }
        ) as resp:
            if resp.status != 200:
                print(f"❌ Failed to add AI: {resp.status}")
            else:
                ai_data = await resp.json()
                print(f"✅ AI Manager added: {ai_data['ai_id']}")
        
        # 5. Get room info (to see available clubs)
        print("\n5. Getting room info...")
        async with session.get(f"{SERVER_URL}/api/rooms/{room_id}") as resp:
            room_info = await resp.json()
            clubs = room_info.get("available_clubs", [])
            if clubs:
                print(f"✅ Found {len(clubs)} clubs")
                # Select first available club
                club_id = clubs[0]["id"]
                club_name = clubs[0]["name"]
                print(f"   Selecting: {club_name} (ID: {club_id})")
                
                # Select club
                async with session.post(
                    f"{SERVER_URL}/api/rooms/{room_id}/select-club",
                    params={"player_id": player_id, "club_id": club_id}
                ) as resp:
                    if resp.status == 200:
                        print(f"✅ Club selected")
                    else:
                        print(f"❌ Failed to select club: {resp.status}")
            else:
                print("❌ No clubs available")
        
        # 6. Start game
        print("\n6. Starting game...")
        async with session.post(
            f"{SERVER_URL}/api/rooms/{room_id}/start",
            params={"player_id": player_id}
        ) as resp:
            if resp.status == 200:
                print("✅ Game started!")
            else:
                print(f"❌ Failed to start: {resp.status}")
                return
        
        # 7. Simulate matchdays
        print("\n7. Simulating matchdays...")
        for i in range(3):
            print(f"\n   Matchday {i+1}...")
            async with session.post(
                f"{SERVER_URL}/api/rooms/{room_id}/simulate-matchday",
                params={"player_id": player_id}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"   ✅ {result.get('message', 'Simulated')}")
                else:
                    print(f"   ❌ Failed: {resp.status}")
            
            # Wait a bit between matchdays
            await asyncio.sleep(1)
        
        # 8. Get final standings
        print("\n8. Getting final standings...")
        async with session.get(f"{SERVER_URL}/api/rooms/{room_id}") as resp:
            final_info = await resp.json()
            standings = final_info.get("standings", [])
            if standings:
                print("\n   Final Standings:")
                print("   " + "-" * 50)
                for s in standings[:5]:  # Top 5
                    print(f"   {s['position']}. {s['club_name']:<20} "
                          f"{s['points']}pts ({s['won']}W {s['drawn']}D {s['lost']}L)")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_multiplayer())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
