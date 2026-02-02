#!/usr/bin/env python3
"""
Test script for LLM-powered AI Manager.

Demonstrates:
- LLM-powered transfer decisions
- LLM tactical preparation
- LLM match decisions (substitutions)
- LLM post-match comments
"""

import sys
from datetime import date, datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel

from fm_manager.core.models import Club, Player, Position
from fm_manager.engine.llm_client import LLMClient, LLMProvider
from fm_manager.engine.ai_manager import (
    AIManager, AIManagerController, AIPersonality, LLMManagerDecisionMaker
)
from fm_manager.engine.transfer_engine import TransferEngine
from fm_manager.engine.finance_engine import ClubFinances

console = Console()


def test_llm_decision_maker():
    """Test the LLM decision maker directly."""
    console.print(Panel("[bold blue]🧠 Testing LLM Decision Maker[/]", border_style="blue"))
    
    # Create mock LLM client
    llm = LLMClient(provider=LLMProvider.MOCK)
    decision_maker = LLMManagerDecisionMaker(llm)
    
    # Create test data
    club = Club(id=1, name="Manchester City", reputation=9500, balance=500_000_000)
    
    from fm_manager.engine.ai_manager import AISquadAssessment
    assessment = AISquadAssessment(
        club_id=1,
        goalkeeper_strength=80,
        defense_strength=85,
        midfield_strength=90,
        attack_strength=88,
        star_players=[1],
    )
    
    player = Player(
        first_name="Erling",
        last_name="Haaland",
        nationality="Norway",
        birth_date=datetime(2000, 7, 21),
        position=Position.ST,
        current_ability=92,
        potential_ability=95,
        club_id=1,
    )
    
    # Create transfer offer
    from fm_manager.engine.transfer_engine import TransferOffer
    offer = TransferOffer(
        player_id=1,
        from_club_id=2,
        to_club_id=1,
        fee=150_000_000,
    )
    
    console.print("\n[bold]Transfer Decision:[/]")
    result = decision_maker.decide_transfer_offer(player, offer, club, assessment)
    console.print(f"  Decision: {result.get('decision', 'unknown').upper()}")
    console.print(f"  Reasoning: {result.get('reasoning', 'N/A')}")
    
    # Test tactical decision
    console.print("\n[bold]Tactical Decision:[/]")
    opponent = Club(id=2, name="Liverpool", reputation=9000)
    key_players = [
        Player(first_name="Kevin", last_name="De Bruyne", position=Position.CM, current_ability=90, nationality="Belgium"),
        Player(first_name="Phil", last_name="Foden", position=Position.LW, current_ability=85, nationality="England"),
    ]
    
    tactics = decision_maker.decide_tactics(opponent, key_players, "Good")
    console.print(f"  Formation: {tactics.get('formation')}")
    console.print(f"  Style: {tactics.get('style')}")
    console.print(f"  Mentality: {tactics.get('mentality')}")
    console.print(f"  Reasoning: {tactics.get('reasoning')}")
    
    # Test substitution decision
    console.print("\n[bold]Substitution Decision:[/]")
    tired_players = [
        Player(first_name="Rodri", last_name="", position=Position.CDM, current_ability=88, nationality="Spain"),
    ]
    available_subs = [
        Player(first_name="Mateo", last_name="Kovacic", position=Position.CM, current_ability=82, nationality="Croatia"),
    ]
    
    sub_decision = decision_maker.decide_substitution(
        minute=75,
        score_for=2,
        score_against=1,
        tired_players=tired_players,
        available_subs=available_subs,
        recent_decisions=[],
    )
    console.print(f"  Make change: {sub_decision.get('make_change')}")
    if sub_decision.get('make_change'):
        console.print(f"  Player out: {sub_decision.get('player_out')}")
        console.print(f"  Player in: {sub_decision.get('player_in')}")
    
    # Test post-match comments
    console.print("\n[bold]Post-Match Comments:[/]")
    comments = decision_maker.generate_post_match_comments(
        won=True,
        drawn=False,
        goals_for=3,
        goals_against=1,
        opponent=opponent,
        key_moments=["Haaland scored twice", "Foden with a brilliant finish"],
    )
    console.print(f"  {comments}")


def test_llm_manager():
    """Test AI Manager with LLM personality."""
    console.print(Panel("[bold green]🎮 Testing LLM-Powered AI Manager[/]", border_style="green"))
    
    # Create LLM client
    llm = LLMClient(provider=LLMProvider.MOCK)
    
    # Create club
    club = Club(
        id=1,
        name="Arsenal",
        reputation=8500,
        balance=200_000_000,
    )
    
    # Create LLM-powered manager
    manager = AIManager(
        club=club,
        personality=AIPersonality.LLM_POWERED,
        llm_client=llm,
    )
    
    console.print(f"\n[bold]Manager Profile:[/]")
    console.print(f"  Club: {manager.club.name}")
    console.print(f"  Personality: {manager.personality.value}")
    console.print(f"  Has LLM: {manager.llm_decision_maker is not None}")
    
    # Create squad
    players = [
        Player(first_name="Aaron", last_name="Ramsdale", position=Position.GK, current_ability=82, nationality="England"),
        Player(first_name="William", last_name="Saliba", position=Position.CB, current_ability=85, nationality="France"),
        Player(first_name="Martin", last_name="Odegaard", position=Position.CAM, current_ability=87, nationality="Norway"),
        Player(first_name="Bukayo", last_name="Saka", position=Position.RW, current_ability=86, nationality="England"),
        Player(first_name="Gabriel", last_name="Jesus", position=Position.ST, current_ability=84, nationality="Brazil"),
    ]
    
    # Assess squad
    console.print(f"\n[bold]Squad Assessment:[/]")
    assessment = manager.assess_squad(players)
    console.print(f"  Defense: {assessment.defense_strength}")
    console.print(f"  Attack: {assessment.attack_strength}")
    console.print(f"  Needs: {[p.value for p in assessment.needs]}")
    
    # Create transfer strategy
    finances = ClubFinances(
        club_id=club.id or 0,
        balance=club.balance,
        wage_budget=3_000_000,
        transfer_budget=100_000_000,
    )
    
    console.print(f"\n[bold]Transfer Strategy:[/]")
    strategy = manager.create_transfer_strategy(finances, players)
    console.print(f"  Budget: €{strategy.max_budget/1e6:.1f}M")
    console.print(f"  Priority positions: {[p.value for p in strategy.priority_positions]}")
    
    # Test LLM tactical preparation
    console.print(f"\n[bold]Tactical Preparation (LLM):[/]")
    opponent = Club(id=2, name="Manchester United", reputation=8800)
    tactics = manager.prepare_match_tactics(opponent, players[:3])
    console.print(f"  Formation: {tactics.get('formation')}")
    console.print(f"  Style: {tactics.get('style')}")
    console.print(f"  Reasoning: {tactics.get('reasoning')}")
    
    # Test post-match comments
    console.print(f"\n[bold]Post-Match Comments (LLM):[/]")
    comments = manager.generate_post_match_comments(
        won=True,
        drawn=False,
        goals_for=2,
        goals_against=0,
        opponent=opponent,
        key_moments=["Saka scored a screamer", "Clean sheet for defense"],
    )
    console.print(f"  {comments}")


def test_controller_with_llm():
    """Test AI Manager Controller with LLM support."""
    console.print(Panel("[bold yellow]🎯 Testing Controller with LLM[/]", border_style="yellow"))
    
    # Create LLM client
    llm = LLMClient(provider=LLMProvider.MOCK)
    
    # Create controller with LLM
    controller = AIManagerController(llm_client=llm)
    
    # Create clubs
    clubs = [
        Club(id=1, name="Chelsea", reputation=8200, balance=300_000_000),
        Club(id=2, name="Newcastle", reputation=7800, balance=250_000_000),
    ]
    
    console.print(f"\n[bold]Creating LLM Managers:[/]")
    
    # Create regular manager
    regular_manager = controller.create_manager(clubs[0], personality=AIPersonality.BALANCED)
    console.print(f"  {clubs[0].name}: {regular_manager.personality.value}")
    console.print(f"    Has LLM: {regular_manager.llm_decision_maker is not None}")
    
    # Create LLM-powered manager
    llm_manager = controller.create_manager(clubs[1], use_llm=True)
    console.print(f"  {clubs[1].name}: {llm_manager.personality.value}")
    console.print(f"    Has LLM: {llm_manager.llm_decision_maker is not None}")
    
    # Create LLM-only personality
    llm_only = controller.create_manager(
        Club(id=3, name="Brighton", reputation=7000, balance=100_000_000),
        personality=AIPersonality.LLM_POWERED,
    )
    console.print(f"  Brighton: {llm_only.personality.value}")
    console.print(f"    Has LLM: {llm_only.llm_decision_maker is not None}")


def main():
    """Run all LLM manager tests."""
    console.print("\n" + "=" * 70)
    console.print("[bold]LLM-POWERED AI MANAGER TEST SUITE[/]")
    console.print("=" * 70 + "\n")
    
    test_llm_decision_maker()
    console.print("\n")
    
    test_llm_manager()
    console.print("\n")
    
    test_controller_with_llm()
    
    console.print("\n" + "=" * 70)
    console.print("[bold green]LLM Manager tests completed![/]")
    console.print("=" * 70)
    
    console.print("\n[bold cyan]Key Features:[/]")
    console.print("  • AIPersonality.LLM_POWERED - Uses LLM for all complex decisions")
    console.print("  • LLMManagerDecisionMaker - Handles transfer/tactical/match decisions")
    console.print("  • Fallback to rule-based when LLM unavailable")
    console.print("  • Post-match comments generated by LLM")


if __name__ == "__main__":
    main()
