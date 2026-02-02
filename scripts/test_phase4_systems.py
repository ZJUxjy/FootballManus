#!/usr/bin/env python3
"""
Test script for Phase 4 LLM integration systems:
- LLM Client
- Narrative Engine
- AI Manager
- News System
- Fan & Board System
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fm_manager.core.models import Club, Player, Position, Match
from fm_manager.engine.match_engine_v2 import MatchEvent
from fm_manager.engine.llm_client import (
    LLMClient, LLMProvider, FMPrompts, create_client_from_env
)
from fm_manager.engine.narrative_engine import (
    NarrativeEngine, MatchNarrativeGenerator, PlayerNarrativeGenerator
)
from fm_manager.engine.ai_manager import (
    AIManager, AIManagerController, AIPersonality, AIStyle
)
from fm_manager.engine.news_system import (
    NewsSystem, NewsCategory, NewsPriority
)
from fm_manager.engine.fan_board_system import (
    FanBoardSystem, FanSystem, BoardSystem, 
    FanSentiment, BoardConfidence
)

console = Console()


def test_llm_client():
    """Test LLM client."""
    console.print(Panel("[bold blue]🤖 Testing LLM Client[/]", border_style="blue"))
    
    # Test mock client
    client = LLMClient(provider=LLMProvider.MOCK)
    
    console.print("\n[bold]Mock Response Test:[/]")
    response = client.generate(
        "Describe a thrilling football match moment",
        system_prompt="You are a sports commentator",
        temperature=0.8,
    )
    
    console.print(f"  Provider: {response.provider.value}")
    console.print(f"  Model: {response.model}")
    console.print(f"  Tokens: {response.tokens_used}")
    console.print(f"  Latency: {response.latency_ms:.1f}ms")
    console.print(f"  Content: {response.content[:80]}...")
    
    # Test caching
    console.print(f"\n[bold]Cache Test:[/]")
    response2 = client.generate(
        "Describe a thrilling football match moment",
        system_prompt="You are a sports commentator",
    )
    console.print(f"  Cache hit: {response2.cached}")
    console.print(f"  Cache size: {client.cache.size}")
    
    # Test usage stats
    console.print(f"\n[bold]Usage Stats:[/]")
    stats = client.get_usage_stats()
    console.print(f"  Total tokens: {stats['total_tokens']}")
    console.print(f"  Est. cost: ${stats['estimated_cost_usd']:.4f}")
    console.print(f"  Requests: {stats['requests_count']}")
    console.print(f"  Cache hits: {stats['cache_hits']}")
    
    # Test prompts
    console.print(f"\n[bold]Prompt Templates:[/]")
    prompt = FMPrompts.MATCH_NARRATIVE.format(
        home_team="Manchester City",
        away_team="Liverpool",
        minute=85,
        event_type="Goal",
        details="Haaland scores a stunning volley",
    )
    console.print(f"  Match narrative prompt length: {len(prompt)} chars")


def test_narrative_engine():
    """Test narrative engine."""
    console.print(Panel("[bold green]📖 Testing Narrative Engine[/]", border_style="green"))
    
    engine = NarrativeEngine()
    
    # Create test data
    home = Club(id=1, name="Manchester City", reputation=9500)
    away = Club(id=2, name="Liverpool", reputation=9000)
    
    match = Match(
        season_id=1,
        home_club_id=1,
        away_club_id=2,
        matchday=1,
        home_score=3,
        away_score=1,
        match_date=date.today(),
    )
    
    from fm_manager.engine.match_engine_v2 import MatchEventType
    events = [
        MatchEvent(minute=15, event_type=MatchEventType.GOAL, team="home", player="Haaland", description="Haaland scores"),
        MatchEvent(minute=45, event_type=MatchEventType.GOAL, team="away", player="Salah", description="Salah equalizes"),
        MatchEvent(minute=67, event_type=MatchEventType.GOAL, team="home", player="Foden", description="Foden puts City ahead"),
        MatchEvent(minute=89, event_type=MatchEventType.GOAL, team="home", player="Haaland", description="Haaland second"),
    ]
    
    # Test match narrative
    console.print("\n[bold]Match Narrative:[/]")
    narrative = engine.generate_match_report(match, events, home, away, use_llm=False)
    
    console.print(f"  Headline: {narrative.headline}")
    console.print(f"  Tone: {narrative.tone}")
    console.print(f"  Key moments: {len(narrative.key_moments)}")
    
    for moment in narrative.key_moments[:3]:
        console.print(f"    {moment['minute']}' - {moment['description'][:60]}...")
    
    # Test player profile
    console.print(f"\n[bold]Player Profile:[/]")
    player = Player(
        first_name="Erling",
        last_name="Haaland",
        nationality="Norway",
        birth_date=datetime(2000, 7, 21),
        position=Position.ST,
        current_ability=92,
        potential_ability=95,
    )
    
    story = engine.generate_player_profile(player, use_llm=False)
    console.print(f"  Traits: {', '.join(story.personality_traits[:3])}")
    console.print(f"  Fan perception: {story.fan_perception}")
    console.print(f"  Highlights: {len(story.career_highlights)}")
    
    # Test season story
    console.print(f"\n[bold]Season Story:[/]")
    season_story = engine.generate_season_review(
        club=home,
        season_year=2024,
        final_position=1,
        key_matches=[match],
        top_scorer=player,
        use_llm=False,
    )
    
    console.print(f"  Title: {season_story.title}")
    console.print(f"  Turning points: {len(season_story.turning_points)}")


def test_ai_manager():
    """Test AI manager."""
    console.print(Panel("[bold yellow]🎮 Testing AI Manager[/]", border_style="yellow"))
    
    controller = AIManagerController()
    
    # Create test clubs
    big_club = Club(id=1, name="Manchester United", reputation=8800, balance=200_000_000)
    small_club = Club(id=2, name="Burnley", reputation=3500, balance=20_000_000)
    
    # Create AI managers with different personalities
    console.print("\n[bold]AI Personalities:[/]")
    
    personalities = [
        (big_club, AIPersonality.SUPERSTAR, "Superstar"),
        (big_club, AIPersonality.YOUTH_FOCUS, "Youth Focus"),
        (small_club, AIPersonality.MONEYBALL, "Moneyball"),
    ]
    
    for club, personality, name in personalities:
        manager = controller.create_manager(club, personality)
        console.print(f"\n  {name} ({club.name}):")
        console.print(f"    Style: {manager.tactics.style.value}")
        console.print(f"    Mentality: {manager.tactics.mentality}")
        console.print(f"    Risk tolerance: {manager.risk_tolerance}")
        console.print(f"    Youth preference: {manager.youth_preference}")
    
    # Test squad assessment
    console.print(f"\n[bold]Squad Assessment:[/]")
    
    test_players = [
        Player(first_name="Test", last_name="GK", position=Position.GK, current_ability=75, birth_date=datetime(1996, 1, 1)),
        Player(first_name="Test", last_name="CB1", position=Position.CB, current_ability=80, birth_date=datetime(1998, 1, 1)),
        Player(first_name="Test", last_name="CB2", position=Position.CB, current_ability=70, birth_date=datetime(2000, 1, 1)),
        Player(first_name="Test", last_name="CM", position=Position.CM, current_ability=65, birth_date=datetime(2002, 1, 1)),
        Player(first_name="Test", last_name="ST", position=Position.ST, current_ability=85, birth_date=datetime(1999, 1, 1)),
    ]
    
    manager = AIManager(big_club, AIPersonality.BALANCED)
    assessment = manager.assess_squad(test_players)
    
    console.print(f"  Defense strength: {assessment.defense_strength}")
    console.print(f"  Attack strength: {assessment.attack_strength}")
    console.print(f"  Needs: {[p.value for p in assessment.needs]}")
    console.print(f"  Star players: {len(assessment.star_players)}")
    
    # Test transfer strategy
    console.print(f"\n[bold]Transfer Strategy:[/]")
    
    from fm_manager.engine.finance_engine import ClubFinances
    finances = ClubFinances(
        club_id=big_club.id or 0,
        balance=big_club.balance,
        wage_budget=3_000_000,
        transfer_budget=100_000_000,
    )
    
    strategy = manager.create_transfer_strategy(finances, test_players)
    console.print(f"  Max budget: €{strategy.max_budget/1e6:.1f}M")
    console.print(f"  Priority positions: {[p.value for p in strategy.priority_positions]}")
    console.print(f"  Age preference: {strategy.age_preference}")
    console.print(f"  Sell threshold: {strategy.sell_threshold}%")


def test_news_system():
    """Test news system."""
    console.print(Panel("[bold magenta]📰 Testing News System[/]", border_style="magenta"))
    
    system = NewsSystem()
    
    # Create test data
    home = Club(id=1, name="Arsenal", reputation=8500)
    away = Club(id=2, name="Chelsea", reputation=8200)
    player = Player(first_name="Bukayo", last_name="Saka", position=Position.RW, current_ability=85, nationality="England")
    
    match = Match(
        season_id=1,
        home_club_id=1,
        away_club_id=2,
        matchday=1,
        home_score=2,
        away_score=1,
        match_date=date.today(),
    )
    
    # Test match news
    console.print("\n[bold]Match Result News:[/]")
    news = system.add_match_result(match, home, away, player)
    console.print(f"  Headline: {news.headline}")
    console.print(f"  Category: {news.category.value}")
    console.print(f"  Priority: {news.priority.value}")
    console.print(f"  Source: {news.source}")
    
    # Test transfer news
    console.print(f"\n[bold]Transfer News:[/]")
    
    transfer_news = system.add_transfer_confirmed(
        player=player,
        from_club=away,
        to_club=home,
        fee=80_000_000,
    )
    console.print(f"  Headline: {transfer_news.headline}")
    console.print(f"  Priority: {transfer_news.priority.value}")
    
    # Test rumor
    rumor = system.add_transfer_rumor(
        player=player,
        from_club=home,
        to_club=away,
        strength="strong",
    )
    console.print(f"\n[bold]Transfer Rumor:[/]")
    console.print(f"  Headline: {rumor.headline}")
    console.print(f"  Priority: {rumor.priority.value}")
    
    # Test injury news
    injury = system.add_injury_news(
        player=player,
        club=home,
        injury_type="hamstring strain",
        duration_weeks=4,
    )
    console.print(f"\n[bold]Injury News:[/]")
    console.print(f"  Headline: {injury.headline}")
    console.print(f"  Category: {injury.category.value}")
    
    # Check feed
    console.print(f"\n[bold]News Feed Summary:[/]")
    latest = system.get_latest_news(count=10)
    console.print(f"  Total items: {len(latest)}")
    
    by_category = {}
    for item in latest:
        cat = item.category.value
        by_category[cat] = by_category.get(cat, 0) + 1
    
    for cat, count in by_category.items():
        console.print(f"    {cat}: {count}")


def test_fan_board_system():
    """Test fan and board system."""
    console.print(Panel("[bold cyan]👥 Testing Fan & Board System[/]", border_style="cyan"))
    
    system = FanBoardSystem()
    
    club = Club(id=1, name="Tottenham", reputation=8000)
    
    # Set board expectations
    console.print("\n[bold]Board Expectations:[/]")
    expectations = system.board_system.set_expectations(club)
    console.print(f"  Target position: {expectations.league_position_target}")
    console.print(f"  Cup target: {expectations.cup_target}")
    console.print(f"  Youth minutes target: {expectations.youth_player_minutes_target}")
    
    # Test fan sentiment progression
    console.print(f"\n[bold]Fan Sentiment Progression:[/]")
    
    results = [
        (True, False, "Win vs Arsenal"),
        (True, False, "Win vs Chelsea"),
        (False, False, "Loss vs Brighton"),
        (False, False, "Loss vs Newcastle"),
        (True, False, "Win vs Villa"),
    ]
    
    sentiment = system.fan_system.get_sentiment(club.id or 0)
    console.print(f"  Initial: {sentiment.get_sentiment_level().value} ({sentiment.overall_score})")
    
    for won, drawn, desc in results:
        sentiment = system.fan_system.update_after_match(club.id or 0, won, drawn)
        console.print(f"  After {desc}: {sentiment.get_sentiment_level().value} ({sentiment.overall_score})")
    
    # Test fan reactions
    console.print(f"\n[bold]Fan Reactions:[/]")
    
    transfer_reaction = system.fan_system.react_to_transfer(
        club_id=club.id or 0,
        player_name="New Signing",
        is_arrival=True,
        fee=50_000_000,
        player_quality=80,
    )
    console.print(f"  Transfer (good): {transfer_reaction}")
    
    injury_reaction = system.fan_system.react_to_injury(
        club_id=club.id or 0,
        player_name="Star Player",
        duration_weeks=8,
        is_key_player=True,
    )
    console.print(f"  Injury (key player): {injury_reaction}")
    
    # Test board evaluation
    console.print(f"\n[bold]Manager Evaluation:[/]")
    
    evaluation = system.board_system.evaluate_manager(
        club_id=club.id or 0,
        current_position=3,
        matches_played=20,
        wins=12,
        draws=4,
        losses=4,
    )
    
    console.print(f"  Overall rating: {evaluation.overall_rating}/100")
    console.print(f"  Confidence: {evaluation.confidence.value}")
    console.print(f"  Summary: {evaluation.get_summary()}")
    console.print(f"  Feedback: {evaluation.recent_feedback[0]}")
    
    # Test job security
    security = system.board_system.check_job_security(club.id or 0)
    console.print(f"\n[bold]Job Security:[/]")
    console.print(f"  Secure: {security['secure']}")
    console.print(f"  Message: {security['message']}")
    
    # Test atmosphere
    console.print(f"\n[bold]Club Atmosphere:[/]")
    atmosphere = system.get_club_atmosphere(club.id or 0)
    console.print(f"  Overall score: {atmosphere['overall_score']}")
    console.print(f"  Atmosphere: {atmosphere['atmosphere']}")
    console.print(f"  Description: {atmosphere['description']}")


def main():
    """Run all Phase 4 tests."""
    console.print("\n" + "=" * 70)
    console.print("[bold]PHASE 4 LLM INTEGRATION TEST SUITE[/]")
    console.print("=" * 70 + "\n")
    
    test_llm_client()
    console.print("\n")
    
    test_narrative_engine()
    console.print("\n")
    
    test_ai_manager()
    console.print("\n")
    
    test_news_system()
    console.print("\n")
    
    test_fan_board_system()
    
    console.print("\n" + "=" * 70)
    console.print("[bold green]All Phase 4 tests completed![/]")
    console.print("=" * 70)


if __name__ == "__main__":
    main()
