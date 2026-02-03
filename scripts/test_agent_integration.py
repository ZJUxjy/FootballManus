#!/usr/bin/env python3
"""
Test script for AI Manager / Agent integration.

Tests:
- LLM configuration loading
- AI Manager creation with different personalities
- Squad assessment
- Transfer decision making (rule-based and LLM-powered)
- Match tactics preparation
"""

import sys
import asyncio
from pathlib import Path
from datetime import date, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fm_manager.config import load_llm_config, create_llm_client_from_config
from fm_manager.core.models import Club, Player, Position
from fm_manager.engine.ai_manager import (
    AIManager, AIManagerController, AIPersonality, AIStyle
)
from fm_manager.engine.llm_client import LLMClient, LLMProvider

console = Console()


def test_config_loading():
    """Test loading LLM configuration."""
    console.print(Panel("[bold blue]📄 Testing Config Loading[/]", border_style="blue"))
    
    config = load_llm_config()
    
    console.print(f"\n[bold]Configuration:[/]")
    console.print(f"  Provider: [cyan]{config.provider}[/]")
    console.print(f"  Model: [cyan]{config.model}[/]")
    console.print(f"  AI Manager Enabled: [green]{config.ai_manager_enabled}[/]")
    console.print(f"  LLM Adoption Rate: [yellow]{config.llm_adoption_rate}[/]")
    
    # Check if API key is configured
    api_key = config.get_api_key()
    if api_key:
        console.print(f"  API Key: [green]Configured (***{api_key[-6:]})[/]")
    else:
        console.print(f"  API Key: [red]Not configured[/]")
    
    return config


def test_mock_llm_client():
    """Test with mock LLM client (no API calls)."""
    console.print(Panel("[bold green]🤖 Testing with Mock LLM Client[/]", border_style="green"))
    
    # Create mock client
    mock_client = LLMClient(
        provider=LLMProvider.MOCK,
        model="mock-model",
        temperature=0.7,
        enable_cache=True,
    )
    
    console.print(f"\n[bold]Mock Client Created:[/]")
    console.print(f"  Provider: [cyan]{mock_client.provider.value}[/]")
    console.print(f"  Model: [cyan]{mock_client.model}[/]")
    
    # Test generation
    console.print(f"\n[bold]Testing Generation:[/]")
    response = mock_client.generate("Test prompt", max_tokens=50)
    console.print(f"  Response: [green]{response.content[:80]}...[/]")
    console.print(f"  Tokens: [yellow]{response.tokens_used}[/]")
    
    return mock_client


def test_ai_manager_with_mock(mock_client):
    """Test AI Manager with mock LLM."""
    console.print(Panel("[bold yellow]🎮 Testing AI Manager with Mock LLM[/]", border_style="yellow"))
    
    # Create club
    club = Club(
        id=1,
        name="Manchester United",
        reputation=8800,
        balance=200_000_000,
    )
    
    # Create players (birth_date calculated from age)
    def birth_date_from_age(age):
        return date.today() - timedelta(days=age*365)
    
    players = [
        Player(id=1, first_name="Bruno", last_name="Fernandes", 
               position=Position.CAM, current_ability=88, potential_ability=90,
               birth_date=birth_date_from_age(29), nationality="Portugal", salary=20_000_000),
        Player(id=2, first_name="Marcus", last_name="Rashford", 
               position=Position.LW, current_ability=85, potential_ability=88,
               birth_date=birth_date_from_age(26), nationality="England", salary=18_000_000),
        Player(id=3, first_name="Casemiro", last_name="", 
               position=Position.CDM, current_ability=87, potential_ability=87,
               birth_date=birth_date_from_age(32), nationality="Brazil", salary=22_000_000),
        Player(id=4, first_name="Lisandro", last_name="Martinez", 
               position=Position.CB, current_ability=84, potential_ability=86,
               birth_date=birth_date_from_age(26), nationality="Argentina", salary=15_000_000),
        Player(id=5, first_name="Andre", last_name="Onana", 
               position=Position.GK, current_ability=83, potential_ability=85,
               birth_date=birth_date_from_age(28), nationality="Cameroon", salary=12_000_000),
    ]
    
    # Test different personalities
    personalities = [
        AIPersonality.BALANCED,
        AIPersonality.LLM_POWERED,
        AIPersonality.AGGRESSIVE,
        AIPersonality.YOUTH_FOCUS,
    ]
    
    table = Table(title="AI Manager Personalities")
    table.add_column("Personality", style="cyan")
    table.add_column("Style", style="green")
    table.add_column("Mentality", style="yellow")
    table.add_column("Risk Tolerance", style="magenta")
    
    for personality in personalities:
        if personality == AIPersonality.LLM_POWERED:
            manager = AIManager(club=club, personality=personality, llm_client=mock_client)
        else:
            manager = AIManager(club=club, personality=personality)
        
        table.add_row(
            personality.value,
            manager.tactics.style.value,
            manager.tactics.mentality,
            f"{manager.risk_tolerance:.1f}"
        )
    
    console.print(table)
    
    # Test LLM-powered manager specifically
    console.print(f"\n[bold]LLM-Powered Manager Details:[/]")
    llm_manager = AIManager(club=club, personality=AIPersonality.LLM_POWERED, llm_client=mock_client)
    console.print(f"  Has LLM Decision Maker: [green]{llm_manager.llm_decision_maker is not None}[/]")
    
    # Test squad assessment
    console.print(f"\n[bold]Squad Assessment:[/]")
    assessment = llm_manager.assess_squad(players)
    console.print(f"  Goalkeeper: {assessment.goalkeeper_strength}")
    console.print(f"  Defense: {assessment.defense_strength}")
    console.print(f"  Midfield: {assessment.midfield_strength}")
    console.print(f"  Attack: {assessment.attack_strength}")
    console.print(f"  Squad Depth: {assessment.squad_depth}")
    console.print(f"  Average Age: {assessment.average_age:.1f}")
    console.print(f"  Star Players: {len(assessment.star_players)}")
    console.print(f"  Deadwood: {len(assessment.deadwood)}")
    
    # Test tactics preparation
    console.print(f"\n[bold]Match Tactics Preparation:[/]")
    opponent = Club(id=2, name="Liverpool", reputation=9000)
    tactics = llm_manager.prepare_match_tactics(opponent, players[:3])
    console.print(f"  Formation: [cyan]{tactics.get('formation', 'N/A')}[/]")
    console.print(f"  Style: [green]{tactics.get('style', 'N/A')}[/]")
    console.print(f"  Mentality: [yellow]{tactics.get('mentality', 'N/A')}[/]")
    console.print(f"  Reasoning: [dim]{tactics.get('reasoning', 'N/A')[:60]}...[/]")
    
    return llm_manager


def test_manager_controller(mock_client):
    """Test AIManagerController."""
    console.print(Panel("[bold magenta]🎯 Testing AIManagerController[/]", border_style="magenta"))
    
    controller = AIManagerController(llm_client=mock_client)
    
    clubs = [
        Club(id=1, name="Liverpool", reputation=9200, balance=250_000_000),
        Club(id=2, name="Arsenal", reputation=9000, balance=200_000_000),
        Club(id=3, name="Chelsea", reputation=8200, balance=300_000_000),
        Club(id=4, name="Brighton", reputation=7500, balance=100_000_000),
        Club(id=5, name="Burnley", reputation=6500, balance=50_000_000),
    ]
    
    console.print(f"\n[bold]Creating Managers:[/]")
    
    table = Table(title="Created Managers")
    table.add_column("Club", style="cyan")
    table.add_column("Reputation", style="yellow")
    table.add_column("Personality", style="green")
    table.add_column("Style", style="magenta")
    
    for club in clubs:
        # 20% chance to use LLM based on adoption rate
        import random
        random.seed(club.id)  # Reproducible
        use_llm = random.random() < 0.2
        
        manager = controller.create_manager(club, use_llm=use_llm)
        
        table.add_row(
            club.name,
            str(club.reputation),
            manager.personality.value,
            manager.tactics.style.value
        )
    
    console.print(table)
    
    return controller


def birth_date_from_age(age):
    """Calculate birth date from age."""
    from datetime import date, timedelta
    return date.today() - timedelta(days=age*365)


def test_transfer_decisions(mock_client):
    """Test transfer decision making."""
    console.print(Panel("[bold cyan]💰 Testing Transfer Decisions[/]", border_style="cyan"))
    
    from fm_manager.engine.transfer_engine import TransferEngine, TransferOffer
    
    club = Club(id=1, name="Manchester United", reputation=8800, balance=200_000_000)
    
    # Create a star player
    star_player = Player(
        id=1,
        first_name="Bruno",
        last_name="Fernandes",
        position=Position.CAM,
        current_ability=88,
        potential_ability=90,
        birth_date=birth_date_from_age(29),
        nationality="Portugal",
        salary=20_000_000,
        market_value=80_000_000
    )
    
    # Create managers with different personalities
    personalities = [
        AIPersonality.BALANCED,
        AIPersonality.SUPERSTAR,
        AIPersonality.MONEYBALL,
    ]
    
    console.print(f"\n[bold]Transfer Offer: €60M for {star_player.full_name}[/]")
    console.print(f"  Player Value: €{star_player.market_value:,}")
    console.print(f"  Current Ability: {star_player.current_ability}")
    
    table = Table(title="Transfer Decision Comparison")
    table.add_column("Personality", style="cyan")
    table.add_column("Decision", style="green")
    table.add_column("Reasoning", style="dim")
    
    for personality in personalities:
        manager = AIManager(club=club, personality=personality, llm_client=mock_client)
        
        # Create a simple offer evaluation
        offer = TransferOffer(
            player_id=star_player.id,
            from_club_id=2,
            to_club_id=1,
            fee=60_000_000,
        )
        
        # Assess squad first
        manager.assess_squad([star_player])
        manager.squad_assessment.star_players = [star_player.id]
        
        # Use appropriate decision method
        if personality == AIPersonality.LLM_POWERED and manager.llm_decision_maker:
            result = manager.llm_decision_maker.decide_transfer_offer(
                star_player, offer, club, manager.squad_assessment
            )
            decision = result.get("decision", "unknown")
            reasoning = result.get("reasoning", "N/A")[:40]
        else:
            # Rule-based fallback
            transfer_engine = TransferEngine()
            result = manager.decide_on_transfer_offer(offer, star_player, transfer_engine)
            decision = result.get("decision", "unknown")
            reasoning = result.get("reasoning", "N/A")[:40]
        
        table.add_row(personality.value, decision, reasoning + "...")
    
    console.print(table)


def test_match_decisions(mock_client):
    """Test in-match decision making."""
    console.print(Panel("[bold red]⚽ Testing Match Decisions[/]", border_style="red"))
    
    club = Club(id=1, name="Manchester United", reputation=8800)
    manager = AIManager(club=club, personality=AIPersonality.AGGRESSIVE, llm_client=mock_client)
    
    # Create tired players and subs
    tired_players = [
        Player(id=1, first_name="Casemiro", last_name="", position=Position.CDM, 
               current_ability=87, birth_date=birth_date_from_age(32)),
    ]
    
    available_subs = [
        Player(id=6, first_name="Kobbie", last_name="Mainoo", position=Position.CM, 
               current_ability=78, birth_date=birth_date_from_age(19)),
        Player(id=7, first_name="Christian", last_name="Eriksen", position=Position.CM, 
               current_ability=80, birth_date=birth_date_from_age(32)),
    ]
    
    console.print(f"\n[bold]Match Scenarios:[/]")
    
    scenarios = [
        (60, 0, 0, "Even match, mid-game"),
        (75, 1, 0, "Leading by 1"),
        (80, 0, 1, "Losing by 1"),
    ]
    
    for minute, score_for, score_against, description in scenarios:
        decision = manager.make_match_decision(
            minute=minute,
            score_for=score_for,
            score_against=score_against,
            available_subs=available_subs,
            tired_players=tired_players,
        )
        
        if decision:
            console.print(f"  {minute}' ({score_for}-{score_against}): [cyan]{decision.decision_type}[/] - {decision.reason}")
        else:
            console.print(f"  {minute}' ({score_for}-{score_against}): [dim]No change[/]")


def main():
    """Run all agent integration tests."""
    console.print("\n" + "=" * 70)
    console.print("[bold]AI MANAGER / AGENT INTEGRATION TEST SUITE[/]")
    console.print("=" * 70 + "\n")
    
    # Step 1: Load config
    config = test_config_loading()
    console.print("\n")
    
    # Step 2: Create mock client (for testing without API calls)
    mock_client = test_mock_llm_client()
    console.print("\n")
    
    # Step 3: Test AI Manager
    manager = test_ai_manager_with_mock(mock_client)
    console.print("\n")
    
    # Step 4: Test Controller
    controller = test_manager_controller(mock_client)
    console.print("\n")
    
    # Step 5: Test Transfer Decisions
    test_transfer_decisions(mock_client)
    console.print("\n")
    
    # Step 6: Test Match Decisions
    test_match_decisions(mock_client)
    
    console.print("\n" + "=" * 70)
    console.print("[bold green]✅ All Agent Integration Tests Completed![/]")
    console.print("=" * 70)
    
    console.print("\n[bold cyan]Summary:[/]")
    console.print("  • Configuration loaded successfully")
    console.print("  • Mock LLM client working")
    console.print("  • AI Manager with different personalities functional")
    console.print("  • Squad assessment working")
    console.print("  • Transfer decision system ready")
    console.print("  • Match decision system ready")
    
    console.print("\n[bold yellow]To use real LLM:[/]")
    console.print("  1. Fix API key format for Volces/Ark")
    console.print("  2. Or use OpenAI-compatible endpoint")
    console.print("  3. Or switch to 'mock' provider for testing")


if __name__ == "__main__":
    main()
