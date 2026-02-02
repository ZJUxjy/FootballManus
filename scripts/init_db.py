#!/usr/bin/env python3
"""Initialize database with seed data."""

import asyncio
import json
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.data.importer import DataImporter
from fm_manager.data.generators import PlayerGenerator


SEEDS_DIR = project_root / "fm_manager" / "data" / "seeds"


def random_club_quality(reputation: int) -> int:
    """Determine average player quality based on club reputation."""
    if reputation >= 9000:  # Elite
        return 78
    elif reputation >= 8000:  # Top
        return 72
    elif reputation >= 6000:  # Good
        return 65
    elif reputation >= 4000:  # Average
        return 58
    else:  # Lower
        return 52


async def seed_database() -> None:
    """Seed database with initial data."""
    print("🚀 Initializing database...")
    
    # Create tables
    await init_db()
    print("✅ Database tables created")
    
    # Get session
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        importer = DataImporter(session)
        
        # Import leagues
        print("📊 Importing leagues...")
        leagues_file = SEEDS_DIR / "leagues.json"
        if leagues_file.exists():
            with open(leagues_file) as f:
                data = json.load(f)
            leagues = await importer.import_leagues(data["leagues"])
            print(f"✅ Imported {len(leagues)} leagues")
            
            # Create mapping of league names to IDs
            league_map = {l.name: l.id for l in leagues}
        else:
            print("❌ Leagues seed file not found")
            league_map = {}
        
        # Import clubs with league IDs
        print("🏟️ Importing clubs...")
        clubs_file = SEEDS_DIR / "clubs.json"
        if clubs_file.exists():
            with open(clubs_file) as f:
                data = json.load(f)
            
            # Update league_id for each club
            for club_data in data["clubs"]:
                league_name = club_data.pop("league_name", None)
                if league_name and league_name in league_map:
                    club_data["league_id"] = league_map[league_name]
            
            clubs = await importer.import_clubs(data["clubs"])
            print(f"✅ Imported {len(clubs)} clubs")
        else:
            print("❌ Clubs seed file not found")
            clubs = []
        
        # Generate players for each club
        print("👤 Generating players...")
        generator = PlayerGenerator(seed=42)
        total_players = 0
        
        for club in clubs:
            players = generator.generate_squad(
                club_id=club.id,
                size=25,
                avg_quality=random_club_quality(club.reputation),
            )
            session.add_all(players)
            total_players += len(players)
        
        await session.commit()
        print(f"✅ Generated {total_players} players")
    
    await close_db()
    print("\n🎉 Database initialization complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
