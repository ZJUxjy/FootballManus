#!/usr/bin/env python3
"""
Test script for Phase 3 core systems:
- Finance Engine
- Transfer Engine
- Youth Engine
"""

import asyncio
import sys
from datetime import date, timedelta, datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from fm_manager.core import get_session_maker, init_db
from fm_manager.core.models import Club, Player, League, Position
from fm_manager.engine.finance_engine import (
    FinanceEngine,
    ClubFinances,
    FinancialTransaction,
    RevenueType,
    ExpenseType,
    format_money,
)
from fm_manager.engine.transfer_engine import (
    TransferEngine,
    TransferOffer,
    ContractOffer,
    OfferType,
    TransferStatus,
)
from fm_manager.engine.youth_engine import (
    YouthEngine,
    YouthAcademy,
    YouthPlayerGenerator,
)
from sqlalchemy import select

console = Console()


def test_finance_engine():
    """Test finance engine."""
    console.print(Panel("[bold blue]💰 Testing Finance Engine[/]", border_style="blue"))
    
    engine = FinanceEngine()
    
    # Create a club
    club = Club(
        id=1,
        name="Manchester City",
        reputation=9500,
        stadium_capacity=53400,
        ticket_price=75,
        balance=500_000_000,
    )
    
    league = League(
        id=1,
        name="Premier League",
        country="England",
        teams_count=20,
    )
    
    # Initialize finances
    finances = ClubFinances(
        club_id=club.id,
        balance=club.balance,
        wage_budget=3_000_000,
        transfer_budget=150_000_000,
    )
    
    console.print(f"\n[bold]Club:[/] {club.name}")
    console.print(f"  Balance: {format_money(finances.balance)}")
    console.print(f"  Wage Budget: {format_money(finances.wage_budget)}/week")
    console.print(f"  Transfer Budget: {format_money(finances.transfer_budget)}")
    
    # Test matchday revenue
    console.print(f"\n[bold]Matchday Revenue Examples:[/]")
    
    for match_type, is_derby, is_title in [
        ("Normal Match", False, False),
        ("Derby", True, False),
        ("Title Race", False, True),
    ]:
        revenue = engine.calculator.calculate_matchday_revenue(
            club, is_derby=is_derby, is_title_race=is_title
        )
        console.print(f"  {match_type}: {format_money(revenue)}")
    
    # Test TV revenue
    console.print(f"\n[bold]TV Revenue:[/]")
    for position in [1, 5, 10, 17]:
        tv_revenue = engine.calculator.calculate_tv_revenue(
            club, league, league_position=position
        )
        console.print(f"  Position {position}: {format_money(tv_revenue)}/match")
    
    # Test commercial revenue
    commercial = engine.calculator.calculate_commercial_revenue(club)
    console.print(f"\n[bold]Commercial Revenue:[/] {format_money(commercial)}/week")
    
    # Test prize money
    console.print(f"\n[bold]End of Season Prize Money:[/]")
    for position in [1, 4, 10, 17]:
        prize = engine.calculator.calculate_season_prize_money(club, league, position)
        console.print(f"  Position {position}: {format_money(prize)}")
    
    # Process a matchday
    console.print(f"\n[bold]Processing Matchday...[/]")
    revenue = engine.process_matchday(finances, club, is_home=True, match_importance="derby")
    console.print(f"  Matchday revenue: {format_money(revenue)}")
    console.print(f"  New balance: {format_money(finances.balance)}")
    
    # Test FFP
    console.print(f"\n[bold]FFP Check:[/]")
    
    # Add some transactions to create a loss
    for i in range(10):
        tx = FinancialTransaction(
            date=date.today() - timedelta(days=i*30),
            amount=5_000_000,
            type=ExpenseType.WAGES,
            description="Monthly wages",
            category="expense",
        )
        finances.add_transaction(tx)
    
    is_compliant, message, sanctions = engine.check_ffp_status(finances, date.today())
    console.print(f"  Status: {message}")
    if sanctions:
        console.print(f"  [red]Potential sanctions:[/]")
        for s in sanctions:
            console.print(f"    - {s}")


def test_transfer_engine():
    """Test transfer engine."""
    console.print(Panel("[bold green]🔄 Testing Transfer Engine[/]", border_style="green"))
    
    engine = TransferEngine()
    engine.initialize_for_season(2024)
    
    # Create clubs
    selling_club = Club(
        id=1,
        name="Arsenal",
        reputation=8500,
        balance=100_000_000,
    )
    
    buying_club = Club(
        id=2,
        name="Barcelona",
        reputation=9000,
        balance=150_000_000,
    )
    
    # Create a player
    birth_date = datetime(2001, 9, 5)  # Bukayo Saka birth date
    player = Player(
        id=1,
        first_name="Bukayo",
        last_name="Saka",
        birth_date=birth_date,
        nationality="England",
        current_ability=85,
        potential_ability=92,
        position=Position.RW,
        salary=200_000,
        market_value=100_000_000,
        club_id=selling_club.id,
    )
    
    console.print(f"\n[bold]Player:[/] {player.full_name}")
    console.print(f"  Age: {player.age}")
    console.print(f"  Current Ability: {player.current_ability}")
    console.print(f"  Market Value: {format_money(player.market_value)}")
    console.print(f"  Current Club: {selling_club.name}")
    
    # Calculate valuation
    value = engine.valuation_calculator.calculate_value(player)
    console.print(f"\n[bold]Calculated Value:[/] {format_money(value)}")
    
    asking_price = engine.valuation_calculator.suggest_asking_price(
        player, selling_club.reputation, buying_club.reputation
    )
    console.print(f"[bold]Suggested Asking Price:[/] {format_money(asking_price)}")
    
    # Create a transfer offer
    offer = engine.create_transfer_offer(
        player=player,
        from_club=buying_club,
        to_club=selling_club,
        fee=80_000_000,
    )
    
    console.print(f"\n[bold]Transfer Offer:[/]")
    console.print(f"  From: {buying_club.name}")
    console.print(f"  Fee: {format_money(offer.fee)}")
    
    # Evaluate offer
    evaluation = engine.evaluate_transfer_offer(offer, player, selling_club, buying_club)
    console.print(f"\n[bold]Offer Evaluation:[/]")
    console.print(f"  Score: {evaluation['score']}/100")
    console.print(f"  Decision: {evaluation['decision'].upper()}")
    console.print(f"  Player Value: {format_money(evaluation['player_value'])}")
    console.print(f"  Fee/Value Ratio: {evaluation['fee_ratio']:.2f}x")
    
    # Test contract negotiation
    console.print(f"\n[bold]Contract Negotiation:[/]")
    
    wage_demand = engine.contract_negotiator.calculate_player_wage_demand(
        player, buying_club.reputation, is_champions_league=True
    )
    console.print(f"  Player Wage Demand: {format_money(wage_demand)}/week")
    
    contract_offer = ContractOffer(
        player_id=player.id,
        club_id=buying_club.id,
        wage=wage_demand + 50_000,  # Offer more than demanded
        contract_length_years=5,
        signing_on_fee=5_000_000,
        squad_role="first_team",
    )
    
    evaluation = engine.contract_negotiator.evaluate_contract_offer(player, contract_offer)
    console.print(f"  Contract Score: {evaluation['score']}/100")
    console.print(f"  Will Accept: {'Yes' if evaluation['will_accept'] else 'No'}")
    console.print(f"  Reasons: {', '.join(evaluation['reasons'])}")
    
    # Test transfer window
    console.print(f"\n[bold]Transfer Window:[/]")
    current_date = date(2024, 7, 15)  # Summer window
    is_open = engine.window_manager.is_window_open(current_date)
    console.print(f"  Date: {current_date}")
    console.print(f"  Window Open: {'Yes' if is_open else 'No'}")
    
    window = engine.window_manager.get_active_window(current_date)
    if window:
        console.print(f"  Window Type: {window.window_type.value}")
        console.print(f"  Days Remaining: {window.days_remaining(current_date)}")


def test_youth_engine():
    """Test youth engine."""
    console.print(Panel("[bold yellow]🌱 Testing Youth Engine[/]", border_style="yellow"))
    
    engine = YouthEngine()
    
    # Create a club with academy
    club = Club(
        id=1,
        name="Manchester United",
        country="England",
        reputation=8800,
    )
    
    academy = YouthAcademy(
        club_id=club.id,
        level=85,  # Excellent academy
        coaching_quality=80,
        facilities_quality=90,
        players_per_intake=4,
    )
    
    console.print(f"\n[bold]Club:[/] {club.name}")
    console.print(f"[bold]Academy Level:[/] {academy.level}/100")
    console.print(f"  Coaching: {academy.coaching_quality}/100")
    console.print(f"  Facilities: {academy.facilities_quality}/100")
    console.print(f"  Quality Factor: {academy.get_intake_quality():.2f}")
    
    # Generate youth intake
    console.print(f"\n[bold]Youth Intake ({academy.players_per_intake} players):[/]")
    
    players = engine.generate_youth_intake(club, academy, date(2024, 3, 1))
    
    table = Table(show_header=True)
    table.add_column("Name", style="white")
    table.add_column("Position", style="cyan")
    table.add_column("Age", justify="right")
    table.add_column("CA", justify="right")
    table.add_column("PA", justify="right")
    table.add_column("Value", justify="right")
    
    for player in players:
        table.add_row(
            player.full_name,
            player.position.value,
            str(player.age),
            str(player.current_ability),
            str(player.potential_ability),
            format_money(player.market_value),
        )
    
    console.print(table)
    
    # Test player development
    console.print(f"\n[bold]Player Development:[/]")
    
    test_player = players[0]
    console.print(f"  Player: {test_player.full_name}")
    console.print(f"  Current: {test_player.current_ability} → Potential: {test_player.potential_ability}")
    
    growth_info = engine.development_calculator.calculate_growth_potential(
        test_player,
        age=test_player.age or 16,
        training_quality=80,
        playing_time=2500,  # Regular starter
    )
    
    console.print(f"\n  Max Growth: +{growth_info['max_growth']} ability points")
    console.print(f"  Likely Growth: +{growth_info['likely_growth']} ability points")
    console.print(f"  Age Factor: {growth_info['age_factor']:.2f}")
    
    # Simulate season development
    result = engine.process_yearly_development(
        test_player,
        playing_time=2500,
        training_quality=80,
        match_ratings=[7.0, 7.5, 6.5, 8.0, 7.0],
    )
    
    console.print(f"\n  [bold]After 1 Season:[/]")
    console.print(f"  {result['old_ability']} → {result['new_ability']} (+{result['growth']})")
    
    # Test scouting
    console.print(f"\n[bold]Scouting Network:[/]")
    
    assignment = engine.scout_region(
        region="Brazil",
        duration_days=30,
        focus_position=Position.ST,
    )
    
    console.print(f"  Assignment: Scout {assignment.region}")
    console.print(f"  Focus: {assignment.focus_position.value if assignment.focus_position else 'Any'}")
    console.print(f"  Duration: {assignment.days_remaining} days")
    
    # Generate scouting report
    report = engine.scouting_network.generate_scouting_report(test_player, scout_quality=75)
    
    console.print(f"\n[bold]Scouting Report for {test_player.full_name}:[/]")
    console.print(f"  CA Estimate: {report.current_ability_estimate} (confidence: {report.confidence}%)")
    console.print(f"  PA Estimate: {report.potential_ability_estimate}")
    console.print(f"  Strengths: {', '.join(report.strengths) if report.strengths else 'None noted'}")
    console.print(f"  Weaknesses: {', '.join(report.weaknesses) if report.weaknesses else 'None noted'}")
    console.print(f"  Recommendation: {report.recommendation.upper()}")


async def test_with_database():
    """Test with real database data."""
    console.print(Panel("[bold magenta]🗄️ Testing with Database[/]", border_style="magenta"))
    
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # Get a club
        result = await session.execute(select(Club).limit(1))
        club = result.scalar_one()
        
        console.print(f"\n[bold]Club from DB:[/] {club.name}")
        console.print(f"  Balance: {format_money(club.balance)}")
        console.print(f"  Reputation: {club.reputation}")
        
        # Get players
        result = await session.execute(
            select(Player).where(Player.club_id == club.id).limit(5)
        )
        players = list(result.scalars().all())
        
        if players:
            console.print(f"\n[bold]Squad Wage Bill:[/]")
            finance_calc = FinanceEngine().calculator
            total_wages = finance_calc.calculate_weekly_wage_bill(players)
            console.print(f"  {len(players)} players: {format_money(total_wages)}/week")
            
            for player in players[:3]:
                console.print(f"    {player.full_name}: {format_money(player.salary)}/week")


def main():
    """Run all tests."""
    console.print("\n" + "=" * 70)
    console.print("[bold]PHASE 3 CORE SYSTEMS TEST SUITE[/]")
    console.print("=" * 70 + "\n")
    
    test_finance_engine()
    console.print("\n")
    
    test_transfer_engine()
    console.print("\n")
    
    test_youth_engine()
    console.print("\n")
    
    asyncio.run(test_with_database())
    
    console.print("\n" + "=" * 70)
    console.print("[bold green]All tests completed![/]")
    console.print("=" * 70)


if __name__ == "__main__":
    main()
