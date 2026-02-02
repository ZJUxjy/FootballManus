#!/usr/bin/env python3
"""
Test script for match engine v2 (shot-based simulation).

This tests the new shot-based system where:
1. Teams create shot chances based on attack vs defense
2. Shots are converted based on shooter vs goalkeeper duel
3. Upsets emerge naturally without artificial probability
"""

import asyncio
import random
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fm_manager.core import get_session_maker, init_db
from fm_manager.core.models import Player, Club
from fm_manager.engine.match_engine_v2 import MatchSimulatorV2, quick_simulate_v2
from fm_manager.data.generators import PlayerGenerator
from sqlalchemy import select


def select_balanced_lineup(squad: list, generator: PlayerGenerator) -> list:
    """Select a balanced 11-player lineup from a squad."""
    from fm_manager.core.models import Position
    
    forwards = [p for p in squad if p.position in {Position.ST, Position.CF, Position.LW, Position.RW}]
    midfielders = [p for p in squad if p.position in {Position.CM, Position.CAM, Position.CDM, Position.LM, Position.RM}]
    defenders = [p for p in squad if p.position in {Position.CB, Position.LB, Position.RB}]
    gks = [p for p in squad if p.position == Position.GK]
    
    lineup = [gks[0]] if gks else []
    lineup.extend(defenders[:4])
    lineup.extend(midfielders[:3])
    lineup.extend(forwards[:3])
    
    return lineup[:11]


def test_shot_creation():
    """Test that shot creation depends on attack vs defense."""
    print("=" * 60)
    print("Test 1: Shot Creation Based on Attack vs Defense")
    print("=" * 60)
    
    # Create teams with different qualities
    generator = PlayerGenerator(seed=42)
    
    # Generate full squads and select balanced lineups
    strong_squad = generator.generate_squad(club_id=1, size=25, avg_quality=80)
    weak_squad = generator.generate_squad(club_id=2, size=25, avg_quality=60)
    
    strong_attack = select_balanced_lineup(strong_squad, generator)
    weak_defense = select_balanced_lineup(weak_squad, generator)
    weak_attack = weak_defense  # Same weak team
    strong_defense = strong_attack  # Same strong team
    
    simulator = MatchSimulatorV2()
    
    # Test multiple matches
    print("\nStrong Attack (80) vs Weak Defense (60):")
    total_shots = 0
    for i in range(10):
        state = simulator.simulate(strong_attack, weak_defense, random_seed=i)
        total_shots += state.home_shots
        print(f"  Match {i+1}: {state.home_shots} shots, {state.home_score} goals")
    print(f"  Average shots: {total_shots/10:.1f}")
    
    print("\nWeak Attack (60) vs Strong Defense (80):")
    total_shots = 0
    for i in range(10):
        state = simulator.simulate(weak_attack, strong_defense, random_seed=i+100)
        total_shots += state.home_shots
        print(f"  Match {i+1}: {state.home_shots} shots, {state.home_score} goals")
    print(f"  Average shots: {total_shots/10:.1f}")


def test_goalkeeper_importance():
    """Test that goalkeeper quality matters."""
    print("\n" + "=" * 60)
    print("Test 2: Goalkeeper Quality Impact")
    print("=" * 60)
    
    # Same attackers vs different keepers
    generator = PlayerGenerator(seed=123)
    attackers_squad = generator.generate_squad(club_id=1, size=25, avg_quality=75)
    attackers = select_balanced_lineup(attackers_squad, generator)
    
    # Create two defenses: one with good keeper, one with bad keeper
    defense_squad = generator.generate_squad(club_id=2, size=25, avg_quality=70)
    good_defense = select_balanced_lineup(defense_squad, generator)
    bad_defense = select_balanced_lineup(defense_squad, generator)
    
    # Manually adjust goalkeeper quality
    for p in good_defense:
        if p.position.value == "GK":
            p.reflexes = 85
            p.handling = 85
            p.current_ability = 85
    
    for p in bad_defense:
        if p.position.value == "GK":
            p.reflexes = 50
            p.handling = 50
            p.current_ability = 50
    
    simulator = MatchSimulatorV2()
    
    print("\nSame Attackers vs Good Keeper (85):")
    goals_against_good = []
    for i in range(20):
        state = simulator.simulate(attackers, good_defense, random_seed=i)
        goals_against_good.append(state.home_score)
    print(f"  Average goals conceded: {sum(goals_against_good)/20:.2f}")
    print(f"  Goals distribution: {sorted(set(goals_against_good))}")
    
    print("\nSame Attackers vs Bad Keeper (50):")
    goals_against_bad = []
    for i in range(20):
        state = simulator.simulate(attackers, bad_defense, random_seed=i+200)
        goals_against_bad.append(state.home_score)
    print(f"  Average goals conceded: {sum(goals_against_bad)/20:.2f}")
    print(f"  Goals distribution: {sorted(set(goals_against_bad))}")
    
    avg_good = sum(goals_against_good) / 20
    avg_bad = sum(goals_against_bad) / 20
    print(f"\n  Difference: {avg_bad - avg_good:.2f} more goals against bad keeper")


def test_upsets_naturally():
    """Test that upsets happen naturally without artificial probability."""
    print("\n" + "=" * 60)
    print("Test 3: Natural Upsets (No Artificial Probability)")
    print("=" * 60)
    
    generator = PlayerGenerator(seed=999)
    
    # Strong team vs weak team
    strong_squad = generator.generate_squad(club_id=1, size=25, avg_quality=80)
    weak_squad = generator.generate_squad(club_id=2, size=25, avg_quality=60)
    
    strong_team = select_balanced_lineup(strong_squad, generator)
    weak_team = select_balanced_lineup(weak_squad, generator)
    
    simulator = MatchSimulatorV2()
    
    results = {"strong_win": 0, "draw": 0, "upset": 0}
    upset_scores = []
    
    print("\nSimulating 100 matches: Strong (80) vs Weak (60)")
    
    for i in range(100):
        state = simulator.simulate(strong_team, weak_team, random_seed=i+500)
        
        if state.home_score > state.away_score:
            results["strong_win"] += 1
        elif state.home_score == state.away_score:
            results["draw"] += 1
        else:
            results["upset"] += 1
            upset_scores.append(f"{state.home_score}-{state.away_score}")
    
    print(f"\nResults:")
    print(f"  Strong team wins: {results['strong_win']} ({results['strong_win']}%)")
    print(f"  Draws: {results['draw']} ({results['draw']}%)")
    print(f"  Upsets (weak wins): {results['upset']} ({results['upset']}%)")
    
    if upset_scores:
        print(f"\n  Upset scores: {', '.join(set(upset_scores))}")
    
    print("\n  Note: Upsets happen naturally through:")
    print("    - Good keeper performance")
    print("    - Poor finishing by strong team")
    print("    - Lucky shots by weak team")
    print("    - Random variation in duels")


def test_shooter_selection():
    """Test that shooters are selected based on position and ability."""
    print("\n" + "=" * 60)
    print("Test 4: Shooter Selection Logic")
    print("=" * 60)
    
    generator = PlayerGenerator(seed=777)
    team_squad = generator.generate_squad(club_id=1, size=25, avg_quality=70)
    team = select_balanced_lineup(team_squad, generator)
    
    simulator = MatchSimulatorV2()
    
    # Track who scores
    scorer_counts = {}
    
    print("\nSimulating 50 matches and tracking scorers...")
    
    for i in range(50):
        # Create a weak opponent just to have a match
        opponent_squad = generator.generate_squad(club_id=2, size=25, avg_quality=60)
        opponent = select_balanced_lineup(opponent_squad, generator)
        state = simulator.simulate(team, opponent, random_seed=i+1000)
        
        for event in state.events:
            if event.event_type.name == "GOAL" and event.team == "home":
                scorer = event.player
                scorer_counts[scorer] = scorer_counts.get(scorer, 0) + 1
    
    print("\nGoal distribution by player:")
    for name, goals in sorted(scorer_counts.items(), key=lambda x: -x[1])[:8]:
        # Find player position
        position = "Unknown"
        for p in team:
            if p.full_name == name:
                position = p.position.value
                break
        print(f"  {name} ({position}): {goals} goals")
    
    # Check that forwards score most
    forward_goals = sum(g for name, g in scorer_counts.items() 
                       for p in team if p.full_name == name and p.position.value in ["ST", "CF", "LW", "RW"])
    total_goals = sum(scorer_counts.values())
    if total_goals > 0:
        print(f"\n  Forwards scored {forward_goals}/{total_goals} ({forward_goals/total_goals*100:.0f}%) of goals")


def test_detailed_stats():
    """Test that detailed stats are tracked."""
    print("\n" + "=" * 60)
    print("Test 5: Detailed Match Statistics")
    print("=" * 60)
    
    generator = PlayerGenerator(seed=555)
    team_a_squad = generator.generate_squad(club_id=1, size=25, avg_quality=75)
    team_b_squad = generator.generate_squad(club_id=2, size=25, avg_quality=70)
    
    team_a = select_balanced_lineup(team_a_squad, generator)
    team_b = select_balanced_lineup(team_b_squad, generator)
    
    simulator = MatchSimulatorV2()
    state = simulator.simulate(team_a, team_b, random_seed=42)
    
    print(f"\nMatch Result: {state.score_string()}")
    print(f"\nHome Team Stats:")
    print(f"  Shots: {state.home_shots}")
    print(f"  On Target: {state.home_shots_on_target}")
    print(f"  Saved: {state.home_shots_saved}")
    print(f"  Missed: {state.home_shots_missed}")
    print(f"  Shot Accuracy: {state.get_shot_accuracy('home'):.1f}%")
    print(f"  Conversion Rate: {state.get_conversion_rate('home'):.1f}%")
    
    print(f"\nAway Team Stats:")
    print(f"  Shots: {state.away_shots}")
    print(f"  On Target: {state.away_shots_on_target}")
    print(f"  Saved: {state.away_shots_saved}")
    print(f"  Missed: {state.away_shots_missed}")
    print(f"  Shot Accuracy: {state.get_shot_accuracy('away'):.1f}%")
    print(f"  Conversion Rate: {state.get_conversion_rate('away'):.1f}%")
    
    print(f"\nPossession: {state.home_possession:.1f}% - {100-state.home_possession:.1f}%")


def test_realistic_scorelines():
    """Test that scorelines are realistic."""
    print("\n" + "=" * 60)
    print("Test 6: Realistic Scoreline Distribution")
    print("=" * 60)
    
    generator = PlayerGenerator(seed=333)
    
    # Equal teams
    team_a_squad = generator.generate_squad(club_id=1, size=25, avg_quality=70)
    team_b_squad = generator.generate_squad(club_id=2, size=25, avg_quality=70)
    
    team_a = select_balanced_lineup(team_a_squad, generator)
    team_b = select_balanced_lineup(team_b_squad, generator)
    
    simulator = MatchSimulatorV2()
    
    scorelines = {}
    total_goals_list = []
    
    print("\nSimulating 200 matches between equal teams...")
    
    for i in range(200):
        state = simulator.simulate(team_a, team_b, random_seed=i+2000)
        score = f"{state.home_score}-{state.away_score}"
        scorelines[score] = scorelines.get(score, 0) + 1
        total_goals_list.append(state.home_score + state.away_score)
    
    print("\nMost common scorelines:")
    for score, count in sorted(scorelines.items(), key=lambda x: -x[1])[:10]:
        bar = "█" * (count // 2)
        print(f"  {score:5} | {bar} {count}")
    
    avg_goals = sum(total_goals_list) / len(total_goals_list)
    print(f"\nAverage goals per match: {avg_goals:.2f} (target: ~2.6)")
    print(f"0-0 draws: {scorelines.get('0-0', 0)} ({scorelines.get('0-0', 0)/2}%)")
    print(f"High scoring (5+): {sum(1 for g in total_goals_list if g >= 5)} matches")


async def test_with_database():
    """Test with real database players."""
    print("\n" + "=" * 60)
    print("Test 7: Simulation with Database Players")
    print("=" * 60)
    
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        result = await session.execute(select(Club).limit(2))
        clubs = result.scalars().all()
        
        if len(clubs) < 2:
            print("Not enough clubs in database")
            return
        
        club_a, club_b = clubs[0], clubs[1]
        print(f"\nMatch: {club_a.name} vs {club_b.name}")
        
        # Get players
        result = await session.execute(
            select(Player).where(Player.club_id == club_a.id).limit(11)
        )
        players_a = list(result.scalars().all())
        
        result = await session.execute(
            select(Player).where(Player.club_id == club_b.id).limit(11)
        )
        players_b = list(result.scalars().all())
        
        if len(players_a) >= 11 and len(players_b) >= 11:
            simulator = MatchSimulatorV2(random_seed=42)
            state = simulator.simulate(players_a, players_b)
            
            print(f"\nFinal Score: {state.score_string()}")
            print(f"\nEvents:")
            for event in state.events:
                if event.event_type.name in ["GOAL", "SHOT_SAVED"]:
                    print(f"  {event.minute}': {event.description}")
            
            print(f"\nStats:")
            print(f"  {club_a.name}: {state.home_shots} shots ({state.home_shots_on_target} on target)")
            print(f"  {club_b.name}: {state.away_shots} shots ({state.away_shots_on_target} on target)")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("MATCH ENGINE V2 TEST SUITE - Shot-Based Simulation")
    print("=" * 70 + "\n")
    
    test_shot_creation()
    test_goalkeeper_importance()
    test_upsets_naturally()
    test_shooter_selection()
    test_detailed_stats()
    test_realistic_scorelines()
    
    # Run async test
    asyncio.run(test_with_database())
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
