#!/usr/bin/env python3
"""英超赛季完整模拟

Usage:
    python scripts/simulate_premier_league_season.py
    python scripts/simulate_premier_league_season.py --export
"""

import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.data.cleaned_data_loader import load_for_match_engine, ClubDataFull, PlayerDataFull
from fm_manager.engine.match_engine_adapter import ClubSquadBuilder, AdaptedPlayer
from fm_manager.engine.match_engine_realistic import RealisticMatchSimulator


@dataclass
class LeagueTableEntry:
    """联赛积分榜条目"""
    club_id: int
    club_name: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    
    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against
    
    def add_match(self, goals_for: int, goals_against: int):
        self.played += 1
        self.goals_for += goals_for
        self.goals_against += goals_against
        
        if goals_for > goals_against:
            self.won += 1
            self.points += 3
        elif goals_for == goals_against:
            self.drawn += 1
            self.points += 1
        else:
            self.lost += 1


@dataclass
class PlayerStats:
    """球员赛季统计"""
    player_id: int
    player_name: str
    club_name: str
    position: str
    current_ability: float
    goals: int = 0
    appearances: int = 0
    
    @property
    def goals_per_game(self) -> float:
        if self.appearances == 0:
            return 0.0
        return self.goals / self.appearances


@dataclass
class MatchResult:
    """比赛结果"""
    matchday: int
    home_club_id: int
    home_club_name: str
    away_club_id: int
    away_club_name: str
    home_goals: int
    away_goals: int
    scorer_ids: list[int] = field(default_factory=list)  # player_ids who scored


class PremierLeagueSeasonSimulator:
    """英超赛季模拟器"""
    
    def __init__(self, random_seed: Optional[int] = None):
        self.rng = random.Random(random_seed)
        self.clubs: dict[int, ClubDataFull] = {}
        self.players: dict[int, PlayerDataFull] = {}
        self.league_table: dict[int, LeagueTableEntry] = {}
        self.player_stats: dict[int, PlayerStats] = {}
        self.match_results: list[MatchResult] = []
        self.club_ids: list[int] = []
        self.season_stats = {
            'total_matches': 0,
            'total_goals': 0,
            'home_wins': 0,
            'draws': 0,
            'away_wins': 0,
            'scorelines': defaultdict(int)
        }
        
    def load_data(self) -> None:
        """加载数据"""
        print("=" * 70)
        print("PREMIER LEAGUE SEASON SIMULATOR")
        print("=" * 70)
        
        all_clubs, all_players = load_for_match_engine()
        
        for club_id, club in all_clubs.items():
            if club.league == "England Premier League":
                self.clubs[club_id] = club
                self.league_table[club_id] = LeagueTableEntry(
                    club_id=club_id,
                    club_name=club.name
                )
        
        for player_id, player in all_players.items():
            if player.club_id in self.clubs:
                self.players[player_id] = player
                self.player_stats[player_id] = PlayerStats(
                    player_id=player_id,
                    player_name=player.name,
                    club_name=player.club_name,
                    position=player.position,
                    current_ability=player.current_ability
                )
        
        self.club_ids = list(self.clubs.keys())
        print(f"\n{len(self.clubs)} clubs, {len(self.players)} players")
        
    def generate_fixtures(self) -> list[list[tuple[int, int]]]:
        """生成赛程（双循环）"""
        n = len(self.club_ids)
        fixtures = []
        
        teams = self.club_ids.copy()
        if n % 2 == 1:
            teams.append(None)
        
        num_teams = len(teams)
        num_rounds = num_teams - 1
        
        for round_num in range(num_rounds):
            round_matches = []
            for i in range(num_teams // 2):
                home = teams[i]
                away = teams[num_teams - 1 - i]
                if home is not None and away is not None:
                    if round_num % 2 == 0:
                        round_matches.append((home, away))
                    else:
                        round_matches.append((away, home))
            fixtures.append(round_matches)
            teams = [teams[0]] + [teams[-1]] + teams[1:-1]
        
        second_half = []
        for round_matches in fixtures:
            second_half.append([(away, home) for home, away in round_matches])
        
        fixtures.extend(second_half)
        return fixtures
    
    def simulate_match(self, home_id: int, away_id: int, matchday: int) -> MatchResult:
        """模拟单场比赛"""
        home_club = self.clubs[home_id]
        away_club = self.clubs[away_id]
        
        home_builder = ClubSquadBuilder(home_club)
        away_builder = ClubSquadBuilder(away_club)
        
        home_lineup = home_builder.build_lineup("4-3-3")
        away_lineup = away_builder.build_lineup("4-3-3")
        
        # 创建名字到player_id的映射（用于匹配进球）
        name_to_id_home = {p.full_name: p._data.id for p in home_lineup if hasattr(p, '_data')}
        name_to_id_away = {p.full_name: p._data.id for p in away_lineup if hasattr(p, '_data')}
        
        # 记录出场球员
        home_player_ids = set(name_to_id_home.values())
        away_player_ids = set(name_to_id_away.values())
        
        simulator = RealisticMatchSimulator(random_seed=self.rng.randint(0, 1000000))
        state = simulator.simulate(
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            home_formation="4-3-3",
            away_formation="4-3-3"
        )
        
        result = MatchResult(
            matchday=matchday,
            home_club_id=home_id,
            home_club_name=home_club.name,
            away_club_id=away_id,
            away_club_name=away_club.name,
            home_goals=state.home_score,
            away_goals=state.away_score
        )
        
        # 记录进球球员ID
        for event in state.events:
            if event.event_type.name == "GOAL":
                scorer_name = event.player
                if event.team == "home":
                    # 在主队阵容中查找
                    for adapted_player in home_lineup:
                        if adapted_player.full_name == scorer_name:
                            if hasattr(adapted_player, '_data'):
                                result.scorer_ids.append(adapted_player._data.id)
                            break
                else:
                    # 在客队阵容中查找
                    for adapted_player in away_lineup:
                        if adapted_player.full_name == scorer_name:
                            if hasattr(adapted_player, '_data'):
                                result.scorer_ids.append(adapted_player._data.id)
                            break
        
        # 更新出场记录
        for pid in home_player_ids:
            if pid in self.player_stats:
                self.player_stats[pid].appearances += 1
        
        for pid in away_player_ids:
            if pid in self.player_stats:
                self.player_stats[pid].appearances += 1
        
        # 更新赛季统计
        self.season_stats['total_matches'] += 1
        self.season_stats['total_goals'] += state.home_score + state.away_score
        self.season_stats['scorelines'][f"{state.home_score}-{state.away_score}"] += 1
        
        if state.home_score > state.away_score:
            self.season_stats['home_wins'] += 1
        elif state.home_score == state.away_score:
            self.season_stats['draws'] += 1
        else:
            self.season_stats['away_wins'] += 1
        
        return result
    
    def update_stats(self, result: MatchResult) -> None:
        """更新统计"""
        # 更新积分榜
        self.league_table[result.home_club_id].add_match(
            result.home_goals, result.away_goals
        )
        self.league_table[result.away_club_id].add_match(
            result.away_goals, result.home_goals
        )
        
        # 更新射手榜（只统计出场球员的进球）
        for player_id in result.scorer_ids:
            if player_id in self.player_stats:
                self.player_stats[player_id].goals += 1
    
    def simulate_season(self) -> None:
        """模拟完整赛季（静默模式）"""
        fixtures = self.generate_fixtures()
        total_matchdays = len(fixtures)
        
        print(f"\nSimulating {total_matchdays} matchdays...")
        
        for matchday_idx, matches in enumerate(fixtures, 1):
            for home_id, away_id in matches:
                result = self.simulate_match(home_id, away_id, matchday_idx)
                self.match_results.append(result)
                self.update_stats(result)
        
        print(f"Completed {self.season_stats['total_matches']} matches")
    
    def simulate_example_match(self, home_id: int, away_id: int) -> None:
        """模拟一场示例比赛并显示详细结果"""
        home_club = self.clubs[home_id]
        away_club = self.clubs[away_id]
        
        home_builder = ClubSquadBuilder(home_club)
        away_builder = ClubSquadBuilder(away_club)
        
        home_lineup = home_builder.build_lineup("4-3-3")
        away_lineup = away_builder.build_lineup("4-3-3")
        
        simulator = RealisticMatchSimulator(random_seed=self.rng.randint(0, 1000000))
        state = simulator.simulate(
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            home_formation="4-3-3",
            away_formation="4-3-3"
        )
        
        print(f"\nExample Match: {home_club.name} vs {away_club.name}")
        print(f"Final Score: {state.score_string()}")
        print(f"\nHome Stats:")
        print(f"  Shots: {state.home_shots}")
        print(f"  On Target: {state.home_shots_on_target}")
        print(f"Away Stats:")
        print(f"  Shots: {state.away_shots}")
        print(f"  On Target: {state.away_shots_on_target}")
    
    def print_table(self, top: int = 20) -> None:
        """打印积分榜"""
        sorted_table = sorted(
            self.league_table.values(),
            key=lambda x: (x.points, x.goal_difference, x.goals_for),
            reverse=True
        )
        
        print(f"\n  {'Pos':<4} {'Club':<25} {'P':<3} {'W':<3} {'D':<3} {'L':<3} {'GF':<4} {'GA':<4} {'GD':<5} {'Pts':<4}")
        print("  " + "-" * 68)
        
        for i, entry in enumerate(sorted_table[:top], 1):
            marker = ""
            if i == 1:
                marker = " 🏆"
            elif i <= 4:
                marker = " 🏆"
            elif i <= 5:
                marker = " 🌍"
            elif i >= 18:
                marker = " 🔻"
            
            print(f"  {i:<4} {entry.club_name:<22}{marker}  {entry.played:<3} {entry.won:<3} "
                  f"{entry.drawn:<3} {entry.lost:<3} {entry.goals_for:<4} "
                  f"{entry.goals_against:<4} {entry.goal_difference:>+4} {entry.points:<4}")
        
        print("  " + "-" * 68)
        print("  Legend: 🏆 Champions League  🌍 Europa League  🔻 Relegated")
    
    def print_season_stats(self) -> None:
        """打印赛季统计"""
        print("\n" + "=" * 70)
        print("SEASON STATISTICS")
        print("=" * 70)
        
        total = self.season_stats['total_matches']
        goals = self.season_stats['total_goals']
        
        print(f"\n  Total Matches:     {total}")
        print(f"  Total Goals:       {goals}")
        print(f"  Avg Goals/Match:   {goals/total:.2f}")
        print(f"\n  Results Distribution:")
        print(f"    Home Wins:       {self.season_stats['home_wins']} ({self.season_stats['home_wins']/total*100:.1f}%)")
        print(f"    Draws:           {self.season_stats['draws']} ({self.season_stats['draws']/total*100:.1f}%)")
        print(f"    Away Wins:       {self.season_stats['away_wins']} ({self.season_stats['away_wins']/total*100:.1f}%)")
        
        print(f"\n  Most Common Scorelines:")
        for score, count in sorted(self.season_stats['scorelines'].items(), key=lambda x: -x[1])[:8]:
            bar = "█" * (count // 2)
            print(f"    {score:5} | {bar} {count}")
    
    def print_top_scorers(self, top: int = 20) -> None:
        """打印射手榜"""
        # 只统计出场次数>=10的球员（避免误差）
        qualified_scorers = [
            p for p in self.player_stats.values() 
            if p.appearances >= 10 and p.goals > 0
        ]
        
        sorted_scorers = sorted(
            qualified_scorers,
            key=lambda x: (x.goals, x.appearances),
            reverse=True
        )
        
        print("\n" + "=" * 70)
        print("TOP SCORERS (min 10 appearances)")
        print("=" * 70)
        print(f"\n  {'Rank':<5} {'Player':<28} {'Club':<22} {'Goals':<6} {'Apps':<5} {'GPG':<5}")
        print("  " + "-" * 70)
        
        for i, player in enumerate(sorted_scorers[:top], 1):
            gpg = f"{player.goals_per_game:.2f}"
            marker = "⚽" if i <= 3 else ""
            print(f"  {i:<5} {player.player_name:<25} {marker:<3} {player.club_name:<22} "
                  f"{player.goals:<6} {player.appearances:<5} {gpg:<5}")
        
        print("  " + "-" * 70)
        
        # 显示统计说明
        print(f"\n  Note: {len([p for p in self.player_stats.values() if p.goals > 0])} players scored, "
              f"{len(qualified_scorers)} qualified (10+ apps)")
    
    def export_results(self, output_dir: str = "data/season_results") -> None:
        """导出赛季结果到CSV"""
        import csv
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 导出积分榜
        with open(f"{output_dir}/premier_league_table.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Rank", "Club", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"])
            sorted_table = sorted(
                self.league_table.values(),
                key=lambda x: (x.points, x.goal_difference, x.goals_for),
                reverse=True
            )
            for i, entry in enumerate(sorted_table, 1):
                writer.writerow([
                    i, entry.club_name, entry.played, entry.won, entry.drawn,
                    entry.lost, entry.goals_for, entry.goals_against,
                    entry.goal_difference, entry.points
                ])
        
        # 导出射手榜（只导出qualified球员）
        with open(f"{output_dir}/top_scorers.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Rank", "Player", "Club", "Goals", "Apps", "GPG"])
            qualified_scorers = [
                p for p in self.player_stats.values() 
                if p.appearances >= 10 and p.goals > 0
            ]
            sorted_scorers = sorted(
                qualified_scorers,
                key=lambda x: (x.goals, x.appearances),
                reverse=True
            )
            for i, player in enumerate(sorted_scorers, 1):
                writer.writerow([
                    i, player.player_name, player.club_name,
                    player.goals, player.appearances, f"{player.goals_per_game:.2f}"
                ])
        
        print(f"\n  Results exported to: {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Premier League Season Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # Run season simulation
  %(prog)s --export     # Export results to CSV
  %(prog)s --seed 42    # Use fixed random seed
        """
    )
    
    parser.add_argument("--export", action="store_true", help="Export results to CSV")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    args.seed = random.randint(0, 1000000)
    simulator = PremierLeagueSeasonSimulator(random_seed=args.seed)
    simulator.load_data()
    
    # 显示一场示例比赛
    club_ids = list(simulator.clubs.keys())
    if len(club_ids) >= 2:
        simulator.simulate_example_match(club_ids[0], club_ids[1])
    
    # 模拟完整赛季
    simulator.simulate_season()
    
    # 打印最终积分榜
    simulator.print_table(top=20)
    
    # 打印赛季统计
    simulator.print_season_stats()
    
    # 打印射手榜
    simulator.print_top_scorers(top=20)
    
    if args.export:
        simulator.export_results()
    
    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
