#!/usr/bin/env python3
"""杯赛模拟程序 - 模拟足总杯和欧冠

展示杯赛系统的功能：
- 足总杯：分级进入、随机抽签、单场淘汰
- 欧冠：小组赛、淘汰赛、两回合制
- 奖金分配
- 比赛统计
"""

import sys
import math
import random
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.data.cleaned_data_loader import load_for_match_engine
from fm_manager.engine.match_engine_adapter import ClubSquadBuilder
from fm_manager.engine.match_engine_markov import EnhancedMarkovEngine as MarkovMatchEngine
from fm_manager.engine.cup_competition_engine import (
    CupDrawGenerator,
    CupPrizeCalculator,
    GroupStanding,
)
from colorama import Fore, Style, init as colorama_init


def simulate_fa_cup():
    """模拟足总杯"""
    colorama_init()
    print("Loading data...")
    clubs, players = load_for_match_engine()

    # 获取英格兰各级联赛球队
    premier_league = [c for c in clubs.values() if c.league == "England Premier League"]
    championship = [c for c in clubs.values() if c.league == "England Championship"]
    league_one = [c for c in clubs.values() if c.league == "England League One"]
    league_two = [c for c in clubs.values() if c.league == "England League Two"]

    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'FA CUP SIMULATION':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")

    print(f"\n参赛球队:")
    print(f"  Premier League: {len(premier_league)} 支")
    print(f"  Championship: {len(championship)} 支")
    print(f"  League One: {len(league_one)} 支")
    print(f"  League Two: {len(league_two)} 支")

    # 简化：只使用英超和英冠球队
    all_teams = premier_league[:20] + championship[:24]
    print(f"\n本次比赛共 {len(all_teams)} 支球队参加")

    # 创建抽签生成器
    draw_gen = CupDrawGenerator(seed=random.randint(1, 1000))

    # 模拟轮次
    rounds = [
        ("第三轮", 32),  # 英超球队加入
        ("第四轮", 16),
        ("第五轮", 8),
        ("四分之一决赛", 4),
        ("半决赛", 2),
        ("决赛", 1),
    ]

    remaining_teams = all_teams.copy()
    round_results = []

    engine = MarkovMatchEngine()

    for round_name, expected_teams in rounds:
        if len(remaining_teams) < 2:
            break

        print(f"\n{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{round_name:^80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}")
        print(f"剩余球队: {len(remaining_teams)} 支")

        # 抽签
        pairings = draw_gen.random_draw(remaining_teams, allow_byes=False)

        winners = []
        match_results = []

        print(f"\n{'主队':<25} {'比分':<8} {'客队':<25} {'胜者':<25}")
        print("-" * 80)

        for home, away in pairings:
            # 构建阵容
            home_lineup = ClubSquadBuilder(home).build_lineup("4-3-3")
            away_lineup = ClubSquadBuilder(away).build_lineup("4-3-3")

            # 模拟比赛
            state = engine.simulate(home_lineup, away_lineup)

            # 确定胜者
            if state.home_score > state.away_score:
                winner = home
                winner_name = home.name
            elif state.away_score > state.home_score:
                winner = away
                winner_name = away.name
            else:
                # 平局则随机
                winner = random.choice([home, away])
                winner_name = winner.name + " (点球)"

            winners.append(winner)
            match_results.append(
                {
                    "home": home.name,
                    "away": away.name,
                    "home_score": state.home_score,
                    "away_score": state.away_score,
                    "winner": winner.name,
                }
            )

            # 显示比赛结果
            score_str = f"{state.home_score}-{state.away_score}"
            print(f"{home.name:<25} {score_str:<8} {away.name:<25} {winner_name:<25}")

        round_results.append(
            {
                "round": round_name,
                "matches": match_results,
                "winners": winners,
            }
        )

        remaining_teams = winners

    # 显示冠军
    if remaining_teams:
        champion = remaining_teams[0]
        print(f"\n{Fore.GREEN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'🏆 FA CUP CHAMPION 🏆':^80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{f'{champion.name}':^80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'=' * 80}{Style.RESET_ALL}")

    return round_results


def simulate_champions_league():
    """模拟欧冠联赛"""
    colorama_init()
    print("Loading data...")
    clubs, players = load_for_match_engine()

    top5_leagues = [
        "England Premier League",
        "La Liga",
        "Bundesliga",
        "Italy Serie A",
        "France Ligue 1",
    ]

    all_top_teams = []
    for league in top5_leagues:
        league_teams = [c for c in clubs.values() if c.league == league]
        league_teams.sort(key=lambda c: c.reputation, reverse=True)
        all_top_teams.extend(league_teams[:4])

    other_teams = [c for c in clubs.values() if c.league not in top5_leagues]
    other_teams.sort(key=lambda c: c.reputation, reverse=True)

    remaining_slots = 32 - len(all_top_teams)
    all_teams = all_top_teams + other_teams[:remaining_slots]
    all_teams = all_teams[:32]

    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'UEFA CHAMPIONS LEAGUE SIMULATION':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"\n参赛球队: {len(all_teams)} 支")

    engine = MarkovMatchEngine()
    draw_gen = CupDrawGenerator(seed=random.randint(1, 1000))

    # ============ 小组赛阶段 ============
    print(f"\n{Fore.MAGENTA}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'GROUP STAGE':^80}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'=' * 80}{Style.RESET_ALL}")

    # 按声望排序并分档
    all_teams.sort(key=lambda c: c.reputation, reverse=True)
    groups = draw_gen.group_stage_draw(all_teams, num_groups=8, clubs_per_group=4)

    group_standings = {}

    for group_name, group_clubs in groups.items():
        print(f"\n{Fore.YELLOW}Group {group_name}:{Style.RESET_ALL}")
        for club in group_clubs:
            print(f"  • {club.name}")

        # 初始化积分榜
        standings = {
            club.id: GroupStanding(
                club_id=club.id,
                club_name=club.name,
            )
            for club in group_clubs
        }

        # 小组赛赛程 (6轮)
        schedules = [
            [(0, 1), (2, 3)],
            [(1, 3), (0, 2)],
            [(3, 0), (1, 2)],
            [(1, 0), (3, 2)],
            [(3, 1), (2, 0)],
            [(0, 3), (2, 1)],
        ]

        for matchday, schedule in enumerate(schedules, 1):
            for home_idx, away_idx in schedule:
                home = group_clubs[home_idx]
                away = group_clubs[away_idx]

                home_lineup = ClubSquadBuilder(home).build_lineup("4-3-3")
                away_lineup = ClubSquadBuilder(away).build_lineup("4-3-3")

                state = engine.simulate(home_lineup, away_lineup)

                # 更新积分榜
                standings[home.id].add_result(state.home_score, state.away_score)
                standings[away.id].add_result(state.away_score, state.home_score)

        # 排序并显示最终排名
        sorted_standings = sorted(
            standings.values(),
            key=lambda s: (s.points, s.goal_difference, s.goals_for),
            reverse=True,
        )

        print(
            f"\n  {'排名':<4} {'球队':<25} {'赛':<3} {'胜':<3} {'平':<3} {'负':<3} {'进':<4} {'失':<4} {'净':<5} {'分':<4}"
        )
        print("  " + "-" * 70)

        for i, team in enumerate(sorted_standings, 1):
            marker = ""
            if i == 1:
                marker = "✓"  # 晋级
            elif i == 2:
                marker = "✓"  # 晋级

            print(
                f"  {i:<4} {team.club_name:<25} {team.played:<3} {team.won:<3} "
                f"{team.drawn:<3} {team.lost:<3} {team.goals_for:<4} {team.goals_against:<4} "
                f"{team.goal_difference:+5d} {team.points:<4} {marker}"
            )

        group_standings[group_name] = sorted_standings

    # ============ 淘汰赛阶段 ============
    print(f"\n{Fore.MAGENTA}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'KNOCKOUT STAGE':^80}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'=' * 80}{Style.RESET_ALL}")

    # 获取小组前两名
    group_winners = []
    group_runners_up = []

    for group_name in sorted(group_standings.keys()):
        standings = group_standings[group_name]
        if len(standings) >= 1:
            # 找到原始club对象
            winner_id = standings[0].club_id
            winner = next(c for c in all_teams if c.id == winner_id)
            group_winners.append(winner)
        if len(standings) >= 2:
            runner_id = standings[1].club_id
            runner = next(c for c in all_teams if c.id == runner_id)
            group_runners_up.append(runner)

    # 淘汰赛轮次
    knockout_rounds = [
        ("八分之一决赛", 16),
        ("四分之一决赛", 8),
        ("半决赛", 4),
        ("决赛", 2),
    ]

    remaining = group_winners + group_runners_up

    for round_name, num_teams in knockout_rounds:
        if len(remaining) < 2:
            break

        print(f"\n{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{round_name:^80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}")

        # 抽签
        random.shuffle(remaining)
        pairings = []
        for i in range(0, len(remaining), 2):
            if i + 1 < len(remaining):
                pairings.append((remaining[i], remaining[i + 1]))

        winners = []

        if round_name == "决赛":
            # 单场决赛
            print(f"\n{'主队':<25} {'比分':<8} {'客队':<25} {'胜者':<25}")
            print("-" * 80)

            for home, away in pairings:
                home_lineup = ClubSquadBuilder(home).build_lineup("4-3-3")
                away_lineup = ClubSquadBuilder(away).build_lineup("4-3-3")

                state = engine.simulate(home_lineup, away_lineup)

                if state.home_score > state.away_score:
                    winner = home
                elif state.away_score > state.home_score:
                    winner = away
                else:
                    winner = random.choice([home, away])

                winners.append(winner)

                score_str = f"{state.home_score}-{state.away_score}"
                print(f"{home.name:<25} {score_str:<8} {away.name:<25} {winner.name:<25}")
        else:
            # 两回合制
            print(f"\n{'对阵':<50} {'首回合':<10} {'次回合':<10} {'总比分':<10} {'胜者':<25}")
            print("-" * 100)

            for home, away in pairings:
                # 首回合
                home_lineup = ClubSquadBuilder(home).build_lineup("4-3-3")
                away_lineup = ClubSquadBuilder(away).build_lineup("4-3-3")
                state1 = engine.simulate(home_lineup, away_lineup)

                # 次回合
                home_lineup2 = ClubSquadBuilder(away).build_lineup("4-3-3")
                away_lineup2 = ClubSquadBuilder(home).build_lineup("4-3-3")
                state2 = engine.simulate(home_lineup2, away_lineup2)

                # 计算总比分
                home_agg = state1.home_score + state2.away_score
                away_agg = state1.away_score + state2.home_score

                if home_agg > away_agg:
                    winner = home
                elif away_agg > home_agg:
                    winner = away
                else:
                    winner = random.choice([home, away])

                winners.append(winner)

                matchup = f"{home.name} vs {away.name}"
                first_leg = f"{state1.home_score}-{state1.away_score}"
                second_leg = f"{state2.home_score}-{state2.away_score}"
                agg = f"{home_agg}-{away_agg}"

                print(f"{matchup:<50} {first_leg:<10} {second_leg:<10} {agg:<10} {winner.name:<25}")

        remaining = winners

    # 显示冠军
    if remaining:
        champion = remaining[0]
        print(f"\n{Fore.GREEN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'🏆 CHAMPIONS LEAGUE WINNER 🏆':^80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{f'{champion.name}':^80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'=' * 80}{Style.RESET_ALL}")

        # 奖金计算
        calculator = CupPrizeCalculator()
        total_prize = (
            calculator.CL_PRIZES["group_stage_participation"]
            + calculator.CL_PRIZES["round_of_16"]
            + calculator.CL_PRIZES["quarter_final"]
            + calculator.CL_PRIZES["semi_final"]
            + calculator.CL_PRIZES["final"]
            + calculator.CL_PRIZES["winner"]
        )
        print(f"\n预估奖金收入: €{total_prize:,.0f}")


def main():
    parser = argparse.ArgumentParser(description="模拟杯赛 (足总杯/欧冠)")
    parser.add_argument(
        "--competition",
        choices=["fa_cup", "champions_league", "all"],
        default="all",
        help="选择要模拟的杯赛",
    )
    args = parser.parse_args()

    if args.competition in ["fa_cup", "all"]:
        simulate_fa_cup()

    if args.competition in ["champions_league", "all"]:
        if args.competition == "all":
            print("\n" + "=" * 80 + "\n")
        simulate_champions_league()


if __name__ == "__main__":
    main()
