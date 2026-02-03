#!/usr/bin/env python3
"""英超赛季模拟 - 使用马尔科夫链引擎"""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.data.cleaned_data_loader import load_for_match_engine
from fm_manager.engine.match_engine_adapter import ClubSquadBuilder
from fm_manager.engine.match_engine_markov import MarkovMatchEngine


def simulate_season():
    print("Loading data...")
    clubs, players = load_for_match_engine()
    
    # Find Premier League clubs
    premier_league = [c for c in clubs.values() if c.league == "England Premier League"]
    if len(premier_league) != 20:
        print(f"Warning: Found {len(premier_league)} clubs, expected 20")
        premier_league = premier_league[:20]
    
    print(f"\nSimulating Premier League with {len(premier_league)} clubs")
    
    # Initialize table
    table = {c.id: {
        "club": c,
        "played": 0, "won": 0, "drawn": 0, "lost": 0,
        "gf": 0, "ga": 0, "gd": 0, "points": 0
    } for c in premier_league}
    
    # Scorers tracking
    scorers = defaultdict(lambda: {"goals": 0, "club": ""})
    
    # Generate fixtures (round-robin)
    fixtures = []
    club_list = premier_league
    n = len(club_list)
    
    for i in range(n - 1):
        for j in range(i + 1, n):
            fixtures.append((club_list[i], club_list[j]))  # Home and away
            fixtures.append((club_list[j], club_list[i]))
    
    print(f"Total matches: {len(fixtures)}")
    
    # Simulate all matches
    engine = MarkovMatchEngine()
    
    for idx, (home, away) in enumerate(fixtures, 1):
        # Build lineups
        home_lineup = ClubSquadBuilder(home).build_lineup("4-3-3")
        away_lineup = ClubSquadBuilder(away).build_lineup("4-3-3")
        
        # Simulate
        state = engine.simulate(home_lineup, away_lineup)
        
        # Update table
        home_stats = table[home.id]
        away_stats = table[away.id]
        
        home_stats["played"] += 1
        away_stats["played"] += 1
        home_stats["gf"] += state.home_score
        home_stats["ga"] += state.away_score
        away_stats["gf"] += state.away_score
        away_stats["ga"] += state.home_score
        
        if state.home_score > state.away_score:
            home_stats["won"] += 1
            away_stats["lost"] += 1
            home_stats["points"] += 3
        elif state.home_score < state.away_score:
            away_stats["won"] += 1
            home_stats["lost"] += 1
            away_stats["points"] += 3
        else:
            home_stats["drawn"] += 1
            away_stats["drawn"] += 1
            home_stats["points"] += 1
            away_stats["points"] += 1
        
        # Track scorers
        for event in state.events:
            if "GOAL" in event.event_type.name and event.player:
                scorers[event.player]["goals"] += 1
                scorers[event.player]["club"] = home.name if event.team == "home" else away.name
        
        if idx % 50 == 0:
            print(f"  Completed {idx}/{len(fixtures)} matches...")
    
    # Sort table
    sorted_table = sorted(table.values(), 
                         key=lambda x: (-x["points"], -x["gd"], -x["gf"]))
    
    # Print table
    print("\n" + "="*70)
    print("PREMIER LEAGUE TABLE")
    print("="*70)
    print(f"{'Pos':<4} {'Club':<25} {'P':<3} {'W':<3} {'D':<3} {'L':<3} {'GF':<4} {'GA':<4} {'GD':<5} {'Pts':<4}")
    print("-"*70)
    
    for i, row in enumerate(sorted_table, 1):
        gd = row["gf"] - row["ga"]
        marker = ""
        if i <= 4:
            marker = "🏆"
        elif i <= 5:
            marker = "🌍"
        elif i >= 18:
            marker = "🔻"
        
        print(f"{i:<4} {row['club'].name:<23} {row['played']:<3} {row['won']:<3} "
              f"{row['drawn']:<3} {row['lost']:<3} {row['gf']:<4} {row['ga']:<4} "
              f"{gd:+4d} {row['points']:<4} {marker}")
    
    # Print top scorers
    print("\n" + "="*50)
    print("TOP SCORERS")
    print("="*50)
    
    sorted_scorers = sorted(scorers.items(), key=lambda x: -x[1]["goals"])[:20]
    for i, (name, data) in enumerate(sorted_scorers, 1):
        print(f"{i:<3} {name:<25} {data['club']:<20} {data['goals']} goals")
    
    # Calculate season stats
    total_goals = sum(r["gf"] for r in table.values())
    total_matches = sum(r["played"] for r in table.values()) // 2
    
    print("\n" + "="*50)
    print("SEASON STATISTICS")
    print("="*50)
    print(f"Total matches: {total_matches}")
    print(f"Total goals: {total_goals}")
    print(f"Avg goals/match: {total_goals/total_matches:.2f}")


if __name__ == "__main__":
    simulate_season()
