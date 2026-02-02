#!/usr/bin/env python3
"""
Test script for the match engine.

This script tests the match simulation with various scenarios:
1. Quick simulation with ratings
2. Full simulation with generated players
3. Validation against real-world statistics
"""

import asyncio
import random
import sys
from collections import defaultdict
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fm_manager.core import get_session_maker, init_db
from fm_manager.core.models import Player, Club, Position
from fm_manager.engine.match_engine import (
    MatchSimulator,
    TeamStrengthCalculator,
    quick_simulate,
)
from fm_manager.data.generators import PlayerGenerator


def test_quick_simulation():
    """Test quick simulation mode."""
    print("=" * 60)
    print("Test 1: Quick Simulation")
    print("=" * 60)
    
    # Test equal teams
    results = []
    for _ in range(100):
        result = quick_simulate(home_rating=75, away_rating=75)
        results.append(result)
    
    home_wins = sum(1 for r in results if r["winner"] == "home")
    draws = sum(1 for r in results if r["winner"] == "draw")
    away_wins = sum(1 for r in results if r["winner"] == "away")
    
    print(f"Equal teams (75 vs 75) - 100 matches:")
    print(f"  Home wins: {home_wins} ({home_wins}%)")
    print(f"  Draws: {draws} ({draws}%)")
    print(f"  Away wins: {away_wins} ({away_wins}%)")
    
    # Test favorite vs underdog
    results = []
    for _ in range(100):
        result = quick_simulate(home_rating=85, away_rating=65)
        results.append(result)
    
    home_wins = sum(1 for r in results if r["winner"] == "home")
    draws = sum(1 for r in results if r["winner"] == "draw")
    away_wins = sum(1 for r in results if r["winner"] == "away")
    
    print(f"\nFavorite vs Underdog (85 vs 65) - 100 matches:")
    print(f"  Home wins: {home_wins} ({home_wins}%)")
    print(f"  Draws: {draws} ({draws}%)")
    print(f"  Away wins: {away_wins} ({away_wins}%)")
    
    # Test sample scores
    print("\nSample matches:")
    for _ in range(5):
        result = quick_simulate(home_rating=78, away_rating=74, random_seed=random.randint(1, 1000))
        print(f"  {result['score']} (xG: {result['home_xg']} - {result['away_xg']})")


def test_team_strength_calculator():
    """Test team strength calculation."""
    print("\n" + "=" * 60)
    print("Test 2: Team Strength Calculator")
    print("=" * 60)
    
    generator = PlayerGenerator(seed=42)
    
    # Create two teams with different qualities
    team_a = generator.generate_squad(club_id=1, size=11, avg_quality=80)
    team_b = generator.generate_squad(club_id=2, size=11, avg_quality=65)
    
    calculator = TeamStrengthCalculator()
    
    strength_a = calculator.calculate(team_a, "4-3-3")
    strength_b = calculator.calculate(team_b, "4-3-3")
    
    print(f"Team A (Quality 80):")
    print(f"  Overall: {strength_a.overall:.1f}")
    print(f"  Attack: {strength_a.attack:.1f}")
    print(f"  Midfield: {strength_a.midfield:.1f}")
    print(f"  Defense: {strength_a.defense:.1f}")
    print(f"  Chemistry: {strength_a.chemistry:.2f}")
    print(f"  Effective Attack: {strength_a.effective_attack():.1f}")
    
    print(f"\nTeam B (Quality 65):")
    print(f"  Overall: {strength_b.overall:.1f}")
    print(f"  Attack: {strength_b.attack:.1f}")
    print(f"  Midfield: {strength_b.midfield:.1f}")
    print(f"  Defense: {strength_b.defense:.1f}")
    print(f"  Chemistry: {strength_b.chemistry:.2f}")
    print(f"  Effective Attack: {strength_b.effective_attack():.1f}")


def test_full_simulation():
    """Test full match simulation."""
    print("\n" + "=" * 60)
    print("Test 3: Full Match Simulation")
    print("=" * 60)
    
    generator = PlayerGenerator(seed=123)
    
    # Create two teams
    home_team = generator.generate_squad(club_id=1, size=11, avg_quality=78)
    away_team = generator.generate_squad(club_id=2, size=11, avg_quality=72)
    
    print(f"Home Team: {len(home_team)} players")
    print(f"Away Team: {len(away_team)} players")
    
    # Run simulation
    simulator = MatchSimulator(random_seed=42)
    
    printed_events = set()
    def print_event(state):
        """Callback to print important events."""
        for event in state.events:
            if event.event_type.name == "GOAL" and id(event) not in printed_events:
                printed_events.add(id(event))
                print(f"  {event.minute}': {event.description}")
    
    print("\nMatch Events:")
    state = simulator.simulate(
        home_lineup=home_team[:11],
        away_lineup=away_team[:11],
        home_formation="4-3-3",
        away_formation="4-4-2",
        callback=print_event,
    )
    
    print(f"\nFinal Score: {state.score_string()}")
    print(f"Status: {state.status.value}")
    
    print(f"\nMatch Statistics:")
    print(f"  Possession: {state.home_possession:.1f}% - {100-state.home_possession:.1f}%")
    print(f"  Shots: {state.home_shots} ({state.home_shots_on_target} on target) - {state.away_shots} ({state.away_shots_on_target} on target)")
    print(f"  Cards: Yellow {state.home_yellows}-{state.away_yellows}, Red {state.home_reds}-{state.away_reds}")
    
    print(f"\nTotal Events: {len(state.events)}")


def test_simulation_validation():
    """Validate simulation against real-world statistics."""
    print("\n" + "=" * 60)
    print("Test 4: Simulation Validation")
    print("=" * 60)
    
    generator = PlayerGenerator(seed=999)
    simulator = MatchSimulator(random_seed=456)
    
    # Run 1000 simulations between equal teams
    results = []
    total_goals = []
    home_goals_list = []
    away_goals_list = []
    
    print("Running 1000 simulations...")
    
    for i in range(1000):
        home_team = generator.generate_squad(club_id=1, size=11, avg_quality=75)
        away_team = generator.generate_squad(club_id=2, size=11, avg_quality=75)
        
        state = simulator.simulate(
            home_lineup=home_team[:11],
            away_lineup=away_team[:11],
        )
        
        results.append({
            "home": state.home_score,
            "away": state.away_score,
            "winner": "home" if state.home_score > state.away_score else (
                "away" if state.away_score > state.home_score else "draw"
            )
        })
        
        total_goals.append(state.home_score + state.away_score)
        home_goals_list.append(state.home_score)
        away_goals_list.append(state.away_score)
    
    # Analyze results
    home_wins = sum(1 for r in results if r["winner"] == "home")
    draws = sum(1 for r in results if r["winner"] == "draw")
    away_wins = sum(1 for r in results if r["winner"] == "away")
    
    avg_goals = sum(total_goals) / len(total_goals)
    avg_home_goals = sum(home_goals_list) / len(home_goals_list)
    avg_away_goals = sum(away_goals_list) / len(away_goals_list)
    
    # Score distribution
    score_dist = defaultdict(int)
    for r in results:
        score_dist[f"{r['home']}-{r['away']}"] += 1
    
    print(f"\nResults (Equal teams):")
    print(f"  Home wins: {home_wins} ({home_wins/10:.1f}%)")
    print(f"  Draws: {draws} ({draws/10:.1f}%)")
    print(f"  Away wins: {away_wins} ({away_wins/10:.1f}%)")
    
    print(f"\nGoals (Real world average ~2.5-2.7 per match):")
    print(f"  Average total goals: {avg_goals:.2f}")
    print(f"  Average home goals: {avg_home_goals:.2f}")
    print(f"  Average away goals: {avg_away_goals:.2f}")
    
    print(f"\nMost common scores:")
    for score, count in sorted(score_dist.items(), key=lambda x: -x[1])[:5]:
        print(f"  {score}: {count} times ({count/10:.1f}%)")
    
    # Validate against real world stats
    print(f"\nValidation:")
    home_win_rate = home_wins / 10
    draw_rate = draws / 10
    
    if 45 <= home_win_rate <= 60:
        print(f"  ✅ Home win rate ({home_win_rate:.1f}%) is realistic (target: ~46%)")
    else:
        print(f"  ⚠️ Home win rate ({home_win_rate:.1f}%) may need adjustment (target: ~46%)")
    
    if 20 <= draw_rate <= 30:
        print(f"  ✅ Draw rate ({draw_rate:.1f}%) is realistic (target: ~26%)")
    else:
        print(f"  ⚠️ Draw rate ({draw_rate:.1f}%) may need adjustment (target: ~26%)")
    
    if 2.0 <= avg_goals <= 3.0:
        print(f"  ✅ Average goals ({avg_goals:.2f}) is realistic (target: ~2.6)")
    else:
        print(f"  ⚠️ Average goals ({avg_goals:.2f}) may need adjustment (target: ~2.6)")


async def test_with_database():
    """Test simulation with real database players."""
    print("\n" + "=" * 60)
    print("Test 5: Simulation with Database Players")
    print("=" * 60)
    
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        from sqlalchemy import select
        
        # Get two clubs
        result = await session.execute(
            select(Club).limit(2)
        )
        clubs = result.scalars().all()
        
        if len(clubs) < 2:
            print("Not enough clubs in database")
            return
        
        club_a, club_b = clubs[0], clubs[1]
        
        print(f"Match: {club_a.name} vs {club_b.name}")
        
        # Get players for each club
        result = await session.execute(
            select(Player).where(Player.club_id == club_a.id).limit(11)
        )
        team_a = result.scalars().all()
        
        result = await session.execute(
            select(Player).where(Player.club_id == club_b.id).limit(11)
        )
        team_b = result.scalars().all()
        
        print(f"  {club_a.name}: {len(team_a)} players")
        print(f"  {club_b.name}: {len(team_b)} players")
        
        if len(team_a) >= 11 and len(team_b) >= 11:
            # Calculate strengths
            calculator = TeamStrengthCalculator()
            strength_a = calculator.calculate(team_a[:11])
            strength_b = calculator.calculate(team_b[:11])
            
            print(f"\n  {club_a.name} strength: {strength_a.overall:.1f}")
            print(f"  {club_b.name} strength: {strength_b.overall:.1f}")
            
            # Simulate
            simulator = MatchSimulator(random_seed=42)
            
            print("\nMatch Events:")
            state = simulator.simulate(
                home_lineup=team_a[:11],
                away_lineup=team_b[:11],
            )
            
            # Print only goals
            for event in state.events:
                if event.event_type.name == "GOAL":
                    print(f"  {event.minute}': {event.description}")
            
            print(f"\n  Final Score: {state.score_string()}")
        else:
            print("  Not enough players for simulation")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MATCH ENGINE TEST SUITE")
    print("=" * 60 + "\n")
    
    # Run synchronous tests
    test_quick_simulation()
    test_team_strength_calculator()
    test_full_simulation()
    test_simulation_validation()
    
    # Run async test
    asyncio.run(test_with_database())
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
