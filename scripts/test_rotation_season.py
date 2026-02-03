#!/usr/bin/env python3
"""测试轮换系统在整个赛季中的效果"""

import sys
import math
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.data.cleaned_data_loader import load_for_match_engine
from fm_manager.engine.match_engine_adapter import ClubSquadBuilder
from fm_manager.engine.rotation_system import MatchImportance, MatchScheduler
from fm_manager.engine.match_engine_markov import MarkovMatchEngine


def simulate_season_with_rotation():
    print("Loading data...")
    clubs, players = load_for_match_engine()

    # Find a team to test (Real Madrid in La Liga)
    test_team = None
    for club in clubs.values():
        if club.league == "La Liga" and 'Real Madrid' in club.name and 'B' not in club.name:
            test_team = club
            break

    if not test_team:
        print("Real Madrid not found, using first La Liga team")
        for club in clubs.values():
            if club.league == "La Liga":
                test_team = club
                break

    print(f"\nTesting with: {test_team.name}")
    print(f"Squad size: {len(test_team.players)}")

    # Create squad builder WITH rotation enabled
    builder = ClubSquadBuilder(test_team, enable_rotation=True)

    # Generate a simple fixture list (10 matches with different opponents)
    print("\n" + "="*80)
    print("SIMULATING SEASON WITH ROTATION")
    print("="*80)

    # Get some La Liga teams as opponents
    opponents = [c for c in clubs.values() if c.league == "La Liga" and c.id != test_team.id][:10]

    if len(opponents) < 5:
        print("Not enough opponents, using any teams")
        opponents = [c for c in clubs.values() if c.id != test_team.id][:10]

    # Track lineup variations
    lineup_tracker = defaultdict(int)
    player_usage = defaultdict(int)

    print(f"\n{'Match':<5} {'Opponent':<25} {'Importance':<12} {'GK':<25} {'ST':<25}")
    print("-"*95)

    for match_num, opponent in enumerate(opponents[:10], 1):
        # Determine match importance
        home_team_name = test_team.name
        away_team_name = opponent.name

        # Simple ranking simulation (random for now)
        home_pos = 1 if "Real" in home_team_name or "Barcelona" in home_team_name else 5
        away_pos = 1 if "Real" in away_team_name or "Barcelona" in away_team_name else 5

        importance = MatchScheduler.determine_match_importance(
            home_team=home_team_name,
            away_team=away_team_name,
            home_league_position=home_pos,
            away_league_position=away_pos,
            is_cup_match=False,
        )

        # Get opponent strength
        opponent_strength = sum(p.current_ability for p in opponent.players) / len(opponent.players)

        # Build lineup with rotation
        lineup = builder.build_lineup(
            formation="4-3-3",
            match_importance=importance,
            opponent_strength=opponent_strength,
            is_home=True,
        )

        if not lineup:
            print(f"{match_num:<5} {'ERROR: Empty lineup!'}")
            continue

        # Track positions
        gk = None
        st = None
        for player in lineup:
            pos = player.position.value if hasattr(player.position, 'value') else str(player.position)
            if pos == "GK" and not gk:
                gk = player.full_name[:23]
            elif pos == "ST" and not st:
                st = player.full_name[:23]

        # Print lineup info
        imp_str = importance.name
        print(f"{match_num:<5} {opponent.name:<25} {imp_str:<12} {gk or 'N/A':<25} {st or 'N/A':<25}")

        # Track player usage
        lineup_signature = tuple(sorted([p.full_name for p in lineup]))
        lineup_tracker[lineup_signature] += 1

        for player in lineup:
            player_usage[player.full_name] += 1

        # Simulate the match to update player fitness
        engine = MarkovMatchEngine()
        home_lineup = lineup
        away_lineup = ClubSquadBuilder(opponent, enable_rotation=False).build_lineup("4-3-3")

        state = engine.simulate(home_lineup, away_lineup)

        # Update rotation system with minutes played
        minutes = {p.id: 90 for p in lineup}
        builder.update_rotation_after_match(lineup, minutes)

    print("\n" + "="*80)
    print("ROTATION ANALYSIS")
    print("="*80)

    print(f"\nUnique lineups used: {len(lineup_tracker)}")
    print(f"Most common lineup used: {max(lineup_tracker.values())} times")

    # Show player usage distribution
    print("\n" + "-"*80)
    print("PLAYER USAGE (matches played)")
    print("-"*80)

    # Sort by usage
    sorted_usage = sorted(player_usage.items(), key=lambda x: x[1], reverse=True)

    print(f"\n{'Player':<25} {'Matches':<8} {'Status':<15}")
    print("-"*50)

    for player, matches in sorted_usage[:20]:
        if matches >= 8:
            status = "🔴 Key Player"
        elif matches >= 5:
            status = "🟡 Regular"
        else:
            status = "🟢 Rotation"
        print(f"{player:<25} {matches:<8} {status:<15}")

    # Get rotation status
    status = builder.get_rotation_status()
    print("\n" + "-"*80)
    print("TEAM FITNESS STATUS")
    print("-"*80)
    print(f"Total players: {status['total_players']}")
    print(f"Players with high fatigue (>60): {status['players_high_fatigue']}")
    print(f"Players with very high fatigue (>80): {status['players_very_high_fatigue']}")
    print(f"Avg matches per player: {status['avg_matches_played']:.2f}")


if __name__ == "__main__":
    simulate_season_with_rotation()
