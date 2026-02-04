"""Integration test for all game systems.

This script tests:
1. Injury system
2. Chemistry system
3. Save/load system
"""

import sys
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fm_manager.core.config import settings
from fm_manager.core.models import Player, Club
from fm_manager.engine.injury_chemistry_engine import InjuryEngine, ChemistryEngine
from fm_manager.core.save_load import SaveLoadManager


class IntegrationTest:
    def __init__(self):
        self.passed_tests = []
        self.failed_tests = []

    def log_pass(self, test_name):
        self.passed_tests.append(test_name)
        print(f"✓ {test_name}")

    def log_fail(self, test_name, reason):
        self.failed_tests.append((test_name, reason))
        print(f"✗ {test_name}: {reason}")

    async def test_injury_engine(self):
        print("\n--- Testing Injury Engine ---")

        try:
            engine = create_async_engine(settings.database_url)
            async_session_maker = async_sessionmaker(engine, class_=AsyncSession)

            async with async_session_maker() as session:
                # Get a player
                result = await session.execute(select(Player).limit(1))
                player = result.scalar_one_or_none()

                if not player:
                    self.log_fail("Injury Engine", "No players in database")
                    return

                injury_engine = InjuryEngine(random_seed=42)

                # Test injury risk calculation
                risk = injury_engine.simulate_injury_risk(
                    player,
                    match_importance="normal",
                    fatigue=50.0,
                    team_chemistry=50.0,
                )

                assert 0.001 <= risk <= 0.05, "Invalid injury risk"

                print(f"  - Player: {player.full_name}")
                print(f"  - Injury risk: {risk:.4f}")

                # Test injury generation
                from datetime import date
                injury = injury_engine.generate_injury(
                    player,
                    player.club_id or 0,
                    date.today()
                )

                assert injury.player_id == player.id, "Injury player mismatch"
                assert injury.status.value == "recovering", "Injury should be recovering"

                print(f"  - Injury type: {injury.injury_type.value}")
                print(f"  - Expected return: {injury.expected_return}")

            self.log_pass("Injury Engine")

        except Exception as e:
            self.log_fail("Injury Engine", str(e))

    async def test_chemistry_engine(self):
        print("\n--- Testing Chemistry Engine ---")

        try:
            engine = create_async_engine(settings.database_url)
            async_session_maker = async_sessionmaker(engine, class_=AsyncSession)

            async with async_session_maker() as session:
                # Get players
                result = await session.execute(select(Player).limit(11))
                players = result.scalars().all()

                if len(players) < 2:
                    self.log_fail("Chemistry Engine", "Not enough players")
                    return

                chemistry_engine = ChemistryEngine(random_seed=42)

                # Test pairwise chemistry
                player1, player2 = players[0], players[1]
                chemistry = chemistry_engine.calculate_pairwise_chemistry(player1, player2)

                assert 0 <= chemistry.compatibility_score <= 100, "Invalid compatibility score"

                print(f"  - {player1.full_name} <-> {player2.full_name}")
                print(f"  - Compatibility: {chemistry.compatibility_score:.1f}")
                print(f"  - Total chemistry: {chemistry.get_total_chemistry():.1f}")

                # Test team chemistry
                if len(players) >= 11:
                    team_scores = chemistry_engine.calculate_team_chemistry(list(players[:11]))
                    modifier = chemistry_engine.get_team_chemistry_modifier(list(players[:11]))

                    print(f"  - Team modifier: {modifier:.3f}")

                    assert 0.8 <= modifier <= 1.2, "Invalid team modifier"

            self.log_pass("Chemistry Engine")

        except Exception as e:
            self.log_fail("Chemistry Engine", str(e))

    async def test_save_load_system(self):
        print("\n--- Testing Save/Load System ---")

        try:
            save_manager = SaveLoadManager()

            # Test loading saves list
            saves = save_manager.get_save_files()
            print(f"  - Found {len(saves)} existing saves")

            self.log_pass("Save/Load System")

        except Exception as e:
            self.log_fail("Save/Load System", str(e))

    async def test_integration(self):
        print("\n=== Running Full Integration Test ===")

        await self.test_injury_engine()
        await self.test_chemistry_engine()
        await self.test_save_load_system()

        # Print summary
        print("\n" + "=" * 50)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 50)
        print(f"\nPassed: {len(self.passed_tests)}")
        print(f"Failed: {len(self.failed_tests)}")

        if self.failed_tests:
            print("\nFailed tests:")
            for name, reason in self.failed_tests:
                print(f"  ✗ {name}: {reason}")
            return False
        else:
            print("\n✓ All tests passed!")
            return True


async def main():
    """Main entry point."""
    print("FM Manager - Integration Test Suite")
    print("=" * 50)

    # Initialize database
    from fm_manager.core.database import init_db
    init_db()

    # Run tests
    test = IntegrationTest()
    success = await test.test_integration()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
