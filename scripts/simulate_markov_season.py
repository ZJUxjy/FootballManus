#!/usr/bin/env python3
"""英超赛季模拟 - 使用马尔科夫链引擎

展示新增的统计功能：
- 助攻榜
- 球员评分榜
- 详细数据导出
- 轮换系统（可选）
"""

import sys
import math
import argparse
from pathlib import Path
from collections import defaultdict
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.data.cleaned_data_loader import load_for_match_engine
from fm_manager.engine.match_engine_adapter import ClubSquadBuilder
from fm_manager.engine.match_engine_markov import MarkovMatchEngine
from fm_manager.engine.match_stats_exporter import SeasonStatsTracker, MatchStatsExporter
from fm_manager.engine.rotation_system import MatchImportance, MatchScheduler
from colorama import Fore, Style, init as colorama_init  # type: ignore[import-not-found]


def simulate_season(enable_rotation: bool = False):
    colorama_init()
    print("Loading data...")
    clubs, players = load_for_match_engine()

    # Find Premier League clubs
    # premier_league = [c for c in clubs.values() if c.league == "La Liga"]
    premier_league = [c for c in clubs.values() if c.league == "England Premier League"]
    if len(premier_league) != 20:
        print(f"Warning: Found {len(premier_league)} clubs, expected 20")
        premier_league = premier_league[:20]

    print(f"\nSimulating Premier League with {len(premier_league)} clubs")
    if enable_rotation:
        print("Rotation system: ENABLED")
    else:
        print("Rotation system: DISABLED")

    # 使用新的 SeasonStatsTracker 来追踪统计
    tracker = SeasonStatsTracker()

    # Create squad builders for each team
    if enable_rotation:
        squad_builders = {club.id: ClubSquadBuilder(club, enable_rotation=True) for club in premier_league}
    else:
        squad_builders = {}

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

    total_matches = len(fixtures)
    bar_len = 30

    for idx, (home, away) in enumerate(fixtures, 1):
        # Build lineups
        if enable_rotation:
            home_builder = squad_builders[home.id]
            away_builder = squad_builders[away.id]

            # Determine match importance
            importance = MatchScheduler.determine_match_importance(
                home_team=home.name,
                away_team=away.name,
                home_league_position=idx % 20 + 1,  # Simple simulated position
                away_league_position=idx % 20 + 1,
                is_cup_match=False,
            )

            opponent_strength_for_home = sum(p.current_ability for p in away.players) / len(away.players)
            opponent_strength_for_away = sum(p.current_ability for p in home.players) / len(home.players)

            home_lineup = home_builder.build_lineup(
                formation="4-3-3",
                match_importance=importance,
                opponent_strength=opponent_strength_for_home,
                is_home=True,
            )
            away_lineup = away_builder.build_lineup(
                formation="4-3-3",
                match_importance=importance,
                opponent_strength=opponent_strength_for_away,
                is_home=False,
            )
        else:
            home_lineup = ClubSquadBuilder(home).build_lineup("4-3-3")
            away_lineup = ClubSquadBuilder(away).build_lineup("4-3-3")

        # Simulate
        state = engine.simulate(home_lineup, away_lineup)

        # 添加到追踪器 - 这会自动累计球员和球队统计
        tracker.add_match(state, home.id, home.name, away.id, away.name)

        # Update rotation system
        if enable_rotation:
            home_minutes = {p.id: 90 for p in home_lineup}
            away_minutes = {p.id: 90 for p in away_lineup}
            squad_builders[home.id].update_rotation_after_match(home_lineup, home_minutes)
            squad_builders[away.id].update_rotation_after_match(away_lineup, away_minutes)

        progress = idx / total_matches
        filled = math.floor(bar_len * progress)
        bar = f"{Fore.GREEN}{'█' * filled}{Style.RESET_ALL}{'░' * (bar_len - filled)}"
        percent = f"{progress * 100:6.2f}%"
        sys.stdout.write(f"\rProgress: [{bar}] {percent} ({idx}/{total_matches})")
        sys.stdout.flush()

    print()

    # ============================================================================
    # 使用新的统计系统输出榜单
    # ============================================================================

    # 打印积分榜
    print("\n" + "="*80)
    print("PREMIER LEAGUE TABLE")
    print("="*80)
    print(f"{'Pos':<4} {'Club':<25} {'P':<3} {'W':<3} {'D':<3} {'L':<3} {'GF':<4} {'GA':<4} {'GD':<5} {'Pts':<5}")
    print("-"*80)

    league_table = tracker.get_league_table()
    for i, team in enumerate(league_table, 1):
        marker = ""
        if i <= 4:
            marker = "🏆"
        elif i <= 5:
            marker = "🌍"
        elif i >= len(league_table) - 2:
            marker = "🔻"

        gd = team.goals_for - team.goals_against
        print(f"{i:<4} {team.team_name:<23} {team.matches_played:<3} {team.wins:<3} "
              f"{team.draws:<3} {team.losses:<3} {team.goals_for:<4} {team.goals_against:<4} "
              f"{gd:+4d} {team.wins * 3 + team.draws:<5} {marker}")

    # 打印射手榜
    print("\n" + "="*80)
    print("TOP SCORERS")
    print("="*80)
    print(f"{'#':<3} {'Player':<25} {'Team':<20} {'Goals':<6} {'Matches':<7} {'G/90':<6}")
    print("-"*80)

    for i, player in enumerate(tracker.get_top_scorers(15), 1):
        g90 = player.get_goals_per_90()
        print(f"{i:<3} {player.player_name:<25} {player.team_name:<20} "
              f"{player.goals:<6} {player.matches_played:<7} {g90:<6.2f}")

    # 打印助攻榜 - 新功能！
    print("\n" + "="*80)
    print("TOP ASSISTS")
    print("="*80)
    print(f"{'#':<3} {'Player':<25} {'Team':<20} {'Assists':<8} {'Matches':<7} {'A/90':<6}")
    print("-"*80)

    for i, player in enumerate(tracker.get_top_assists(15), 1):
        a90 = player.get_assists_per_90()
        print(f"{i:<3} {player.player_name:<25} {player.team_name:<20} "
              f"{player.assists:<8} {player.matches_played:<7} {a90:<6.2f}")

    # 打印评分榜 - 新功能！
    print("\n" + "="*80)
    print("TOP RATED PLAYERS (min 5 matches)")
    print("="*80)
    print(f"{'#':<3} {'Player':<25} {'Team':<20} {'Pos':<5} {'Rating':<7} {'Matches':<7}")
    print("-"*80)

    for i, player in enumerate(tracker.get_top_rated(15, min_matches=5), 1):
        pos = player.position or 'N/A'
        print(f"{i:<3} {player.player_name:<25} {player.team_name:<20} "
              f"{pos:<5} {player.avg_rating:<7.2f} {player.matches_played:<7}")

    # 赛季统计摘要
    total_goals = sum(t.goals_for for t in tracker.team_stats.values())
    total_matches = sum(t.matches_played for t in tracker.team_stats.values()) // 2

    print("\n" + "="*80)
    print("SEASON STATISTICS")
    print("="*80)
    print(f"Total matches: {total_matches}")
    print(f"Total goals: {total_goals}")
    print(f"Avg goals/match: {total_goals/total_matches:.2f}")
    print(f"Total players tracked: {len(tracker.player_stats)}")

    # 导出数据到文件
    print("\n" + "="*80)
    print("EXPORTING DATA")
    print("="*80)

    output_dir = Path("/tmp/season_stats")
    output_dir.mkdir(exist_ok=True)

    # 导出 JSON
    MatchStatsExporter.export_leaderboards(tracker, output_dir)
    print(f"✓ Exported leaderboards to {output_dir}/")

    # 导出 CSV
    MatchStatsExporter.export_team_stats_to_csv(tracker, output_dir / "teams.csv")
    MatchStatsExporter.export_player_stats_to_csv(tracker, output_dir / "players.csv")
    print(f"✓ Exported CSV files to {output_dir}/")

    # 显示一些球员详细数据示例
    print("\n" + "="*80)
    print("PLAYER STATS EXAMPLE (Top scorer details)")
    print("="*80)
    top_scorer = tracker.get_top_scorers(1)[0]
    print(f"\n{top_scorer.player_name} - {top_scorer.team_name}")
    print(f"  Goals: {top_scorer.goals} | Assists: {top_scorer.assists} | Avg Rating: {top_scorer.avg_rating:.2f}")
    print(f"  Shots: {top_scorer.shots} (Shot accuracy: {top_scorer.get_shot_accuracy():.1f}%)")
    print(f"  Passes: {top_scorer.passes_attempted} (Pass accuracy: {top_scorer.get_pass_accuracy():.1f}%)")
    print(f"  Key Passes: {top_scorer.key_passes} | Dribbles: {top_scorer.dribbles}")
    print(f"  Tackles: {top_scorer.tackles} | Interceptions: {top_scorer.interceptions}")

    if top_scorer.position == 'GK':
        print(f"  Saves: {top_scorer.saves} | Clean Sheets: {top_scorer.clean_sheets} | Goals Conceded: {top_scorer.goals_conceded}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a football season with optional rotation system")
    parser.add_argument("--rotation", action="store_true", help="Enable squad rotation system")
    args = parser.parse_args()

    simulate_season(enable_rotation=args.rotation)
