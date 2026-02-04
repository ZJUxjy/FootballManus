"""Test the enhanced Markov engine."""

from fm_manager.engine.match_engine_markov_v2 import EnhancedMarkovEngine
from fm_manager.core.database import get_db_session
from fm_manager.core.models import Player

async def test_engine():
    """Test the enhanced engine."""
    async with get_db_session() as session:
        # Get some players
        from sqlalchemy import select
        result = await session.execute(select(Player).limit(22))
        players = list(result.scalars().all())

        if len(players) < 22:
            print("Not enough players in database")
            return

        # Create teams
        home_team = players[:11]
        away_team = players[11:22]

        # Create engine
        engine = EnhancedMarkovEngine(random_seed=42)

        # Simulate a match
        print("Simulating match...")
        match_state = engine.simulate(
            home_lineup=home_team,
            away_lineup=away_team,
            home_formation="4-3-3",
            away_formation="4-4-2"
        )

        print(f"Final Score: {match_state.home_score}-{match_state.away_score}")
        print(f"Home shots: {match_state.home_shots} (on target: {match_state.home_shots_on_target})")
        print(f"Away shots: {match_state.away_shots} (on target: {match_state.away_shots_on_target})")
        print(f"Home possession: {match_state.home_possession:.1f}%")
        print(f"Total events: {len(match_state.events)}")

        # Show some player ratings
        print("\nHome player ratings:")
        for name, stats in match_state.home_player_stats.items():
            if stats.minutes_played >= 90:
                print(f"  {name}: {stats.match_rating:.1f}")

        print("\nAway player ratings:")
        for name, stats in match_state.away_player_stats.items():
            if stats.minutes_played >= 90:
                print(f"  {name}: {stats.match_rating:.1f}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_engine())
