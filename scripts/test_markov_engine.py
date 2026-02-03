#!/usr/bin/env python3
"""Test the Markov chain match engine."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.data.cleaned_data_loader import load_for_match_engine
from fm_manager.engine.match_engine_adapter import ClubSquadBuilder
from fm_manager.engine.match_engine_markov import MarkovMatchEngine


def main():
    print("Loading data...")
    clubs, players = load_for_match_engine()
    
    # Find Man City and Liverpool
    man_city = None
    liverpool = None
    
    for club in clubs.values():
        if "Man City" in club.name or "Manchester City" in club.name:
            man_city = club
        if club.name == "Liverpool":
            liverpool = club
    
    if not man_city or not liverpool:
        print("Teams not found!")
        return
    
    print(f"\nMatch: {man_city.name} vs {liverpool.name}")
    
    # Build lineups
    home_builder = ClubSquadBuilder(man_city)
    away_builder = ClubSquadBuilder(liverpool)
    
    home_lineup = home_builder.build_lineup("4-3-3")
    away_lineup = away_builder.build_lineup("4-3-3")
    
    print(f"Home lineup: {[p.full_name for p in home_lineup[:3]]}...")
    print(f"Away lineup: {[p.full_name for p in away_lineup[:3]]}...")
    
    # Simulate match
    engine = MarkovMatchEngine(random_seed=42)
    
    print("\nSimulating match...")
    state = engine.simulate(home_lineup, away_lineup)
    
    print(f"\n{'='*60}")
    print(f"FINAL SCORE: {state.home_score} - {state.away_score}")
    print(f"{'='*60}")
    
    print(f"\nStatistics:")
    print(f"  Shots: {state.home_shots} - {state.away_shots}")
    print(f"  On Target: {state.home_shots_on_target} - {state.away_shots_on_target}")
    print(f"  Passes: {state.home_passes} - {state.away_passes}")
    print(f"  Corners: {state.home_corners} - {state.away_corners}")
    print(f"  Fouls: {state.home_fouls} - {state.away_fouls}")
    
    print(f"\nKey Events:")
    goals = [e for e in state.events if "GOAL" in e.event_type.name]
    cards = [e for e in state.events if "CARD" in e.event_type.name]
    
    for g in goals:
        print(f"  {g.minute}' - {g.description}")
    for c in cards[:3]:  # Show max 3 cards
        print(f"  {c.minute}' - {c.description}")
    
    print(f"\nTotal events: {len(state.events)}")


if __name__ == "__main__":
    main()
