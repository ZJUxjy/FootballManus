#!/usr/bin/env python3
"""Demo script to simulate matches using cleaned FM data.

Usage:
    python scripts/demo_match_simulation.py
    python scripts/demo_match_simulation.py --match "Man City" "Liverpool"
    python scripts/demo_match_simulation.py --list-leagues
    python scripts/demo_match_simulation.py --list-clubs "Premier League"
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.engine.match_engine_adapter import (
    MatchSimulatorWithRealData,
    simulate_match_between,
)


def print_match_result(result: dict) -> None:
    """Pretty print match result."""
    print("\n" + "=" * 60)
    print("🏆 比赛结果")
    print("=" * 60)
    
    home = result["home_club"]
    away = result["away_club"]
    home_score = result["home_score"]
    away_score = result["away_score"]
    
    if home_score > away_score:
        winner_text = f"🎉 {home} 获胜!"
    elif away_score > home_score:
        winner_text = f"🎉 {away} 获胜!"
    else:
        winner_text = "🤝 平局"
    
    print(f"\n{home} {home_score} - {away_score} {away}")
    print(f"{winner_text}\n")
    
    print("-" * 60)
    print("📋 比赛事件")
    print("-" * 60)
    
    goals = [e for e in result["events"] if e["type"] == "GOAL"]
    cards = [e for e in result["events"] if "CARD" in e["type"]]
    
    if goals:
        print("\n⚽ 进球:")
        for goal in goals:
            team_icon = "🏠" if goal["team"] == "home" else "✈️"
            print(f"  {team_icon} {goal['minute']}' - {goal['player']}")
    
    if cards:
        print("\n🟨🟥 红黄牌:")
        for card in cards:
            team_icon = "🏠" if card["team"] == "home" else "✈️"
            card_icon = "🟥" if card["type"] == "RED_CARD" else "🟨"
            print(f"  {team_icon} {card['minute']}' {card_icon} {card['player']}")
    
    print("\n" + "-" * 60)
    print("📊 比赛统计")
    print("-" * 60)
    stats = result["stats"]
    print(f"  射门:            {home} {stats['home_shots']} - {stats['away_shots']} {away}")
    print(f"  射正:            {home} {stats['home_shots_on_target']} - {stats['away_shots_on_target']} {away}")
    print(f"  控球率:          {home} {stats['home_possession']}% - {stats['away_possession']}% {away}")
    
    print("=" * 60)


def list_leagues():
    """List all available leagues."""
    print("\n正在加载联赛数据...")
    simulator = MatchSimulatorWithRealData()
    leagues = simulator.get_available_leagues()
    
    print(f"\n📚 可用联赛列表 (共 {len(leagues)} 个):")
    print("-" * 60)
    
    for i, league in enumerate(sorted(leagues)[:50], 1):
        print(f"  {i:2d}. {league}")
    
    if len(leagues) > 50:
        print(f"  ... and {len(leagues) - 50} more")
    
    print("-" * 60)


def list_clubs(league_name: str):
    """List clubs in a league."""
    print(f"\n正在加载 {league_name} 的俱乐部数据...")
    simulator = MatchSimulatorWithRealData()
    simulator.load_data()
    
    clubs = simulator.list_clubs_in_league(league_name)
    
    if not clubs:
        print(f"❌ 未找到联赛: {league_name}")
        print("尝试使用: 'England Premier League', 'La Liga', 'Italy Serie A'")
        return
    
    print(f"\n⚽ {league_name} 俱乐部列表 (共 {len(clubs)} 个):")
    print("-" * 80)
    print(f"{'排名':<4} {'俱乐部':<25} {'国家':<15} {'球员数':<8} {'平均能力':<8}")
    print("-" * 80)
    
    sorted_clubs = sorted(clubs, key=lambda c: c.reputation, reverse=True)
    
    for i, club in enumerate(sorted_clubs[:30], 1):
        from fm_manager.engine.match_engine_adapter import ClubSquadBuilder
        builder = ClubSquadBuilder(club)
        summary = builder.get_squad_summary()
        
        player_count = summary["total_players"]
        avg_ability = summary["avg_ability"]
        
        print(f"{i:<4} {club.name:<25} {club.country:<15} {player_count:<8} {avg_ability:<8}")
    
    if len(clubs) > 30:
        print(f"\n... 还有 {len(clubs) - 30} 个俱乐部")
    
    print("-" * 80)


def run_demo_match():
    """Run a demo match between two top clubs."""
    print("\n⚽ 演示比赛: 曼城 vs 利物浦")
    print("=" * 60)
    
    try:
        result = simulate_match_between(
            home_club_name="Man City",
            away_club_name="Liverpool",
            home_formation="4-3-3",
            away_formation="4-3-3",
            random_seed=42,
        )
        print_match_result(result)
    except ValueError as e:
        print(f"❌ 错误: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Demo match simulation using cleaned FM data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 运行演示比赛
  %(prog)s --match "Man City" "Liverpool"  # 模拟指定比赛
  %(prog)s --list-leagues           # 列出所有联赛
  %(prog)s --list-clubs "England Premier League"   # 列出联赛俱乐部
        """
    )
    
    parser.add_argument("--match", nargs=2, metavar=("HOME", "AWAY"),
                        help="模拟两支球队之间的比赛")
    parser.add_argument("--list-leagues", action="store_true",
                        help="列出所有可用联赛")
    parser.add_argument("--list-clubs", metavar="LEAGUE",
                        help="列出指定联赛的所有俱乐部")
    parser.add_argument("--seed", type=int, default=None,
                        help="随机种子（用于可重复的结果）")
    
    args = parser.parse_args()
    
    if args.list_leagues:
        list_leagues()
    elif args.list_clubs:
        list_clubs(args.list_clubs)
    elif args.match:
        home, away = args.match
        print(f"\n⚽ 比赛: {home} vs {away}")
        result = simulate_match_between(home, away, random_seed=args.seed)
        print_match_result(result)
    else:
        run_demo_match()


if __name__ == "__main__":
    main()
