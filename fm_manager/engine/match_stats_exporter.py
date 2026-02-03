"""Match statistics export and tracking system.

Provides functionality to export match statistics in various formats
(JSON, CSV) and track season-long statistics.
"""

import csv
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict


@dataclass
class PlayerSeasonStats:
    """Accumulated statistics for a player over a season."""
    player_id: int
    player_name: str
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    position: Optional[str] = None

    # Match participation
    matches_played: int = 0
    minutes_played: int = 0

    # Offensive stats
    goals: int = 0
    assists: int = 0
    shots: int = 0
    shots_on_target: int = 0
    key_passes: int = 0
    crosses: int = 0
    crosses_successful: int = 0
    dribbles: int = 0
    dribbles_failed: int = 0
    big_chances_created: int = 0
    big_chances_missed: int = 0
    through_balls: int = 0

    # Passing stats
    passes_attempted: int = 0
    passes_completed: int = 0

    # Defensive stats
    tackles: int = 0
    interceptions: int = 0
    blocks: int = 0
    clearances: int = 0
    aerial_duels_won: int = 0
    aerial_duels_lost: int = 0
    offsides: int = 0

    # Goalkeeper stats
    saves: int = 0
    saves_caught: int = 0
    saves_parried: int = 0
    punches: int = 0
    one_on_one_saves: int = 0
    high_claims: int = 0
    goals_conceded: int = 0
    clean_sheets: int = 0

    # Discipline
    yellow_cards: int = 0
    red_cards: int = 0
    own_goals: int = 0

    # Ratings
    total_rating: float = 0.0
    avg_rating: float = 0.0

    def add_match_stats(self, match_stats: object) -> None:
        """Add statistics from a single match."""
        self.matches_played += 1

        # Use getattr to safely access fields that may or may not exist
        self.minutes_played += getattr(match_stats, 'minutes_played', 0)
        self.goals += getattr(match_stats, 'goals', 0)
        self.assists += getattr(match_stats, 'assists', 0)
        self.shots += getattr(match_stats, 'shots', 0)
        self.shots_on_target += getattr(match_stats, 'shots_on_target', 0)
        self.key_passes += getattr(match_stats, 'key_passes', 0)
        self.crosses += getattr(match_stats, 'crosses', 0)
        self.crosses_successful += getattr(match_stats, 'crosses_successful', 0)
        self.dribbles += getattr(match_stats, 'dribbles', 0)
        self.dribbles_failed += getattr(match_stats, 'dribbles_failed', 0)
        self.big_chances_created += getattr(match_stats, 'big_chances_created', 0)
        self.big_chances_missed += getattr(match_stats, 'big_chances_missed', 0)
        self.through_balls += getattr(match_stats, 'through_balls', 0)

        self.passes_attempted += getattr(match_stats, 'passes_attempted', 0)
        self.passes_completed += getattr(match_stats, 'passes_completed', 0)

        self.tackles += getattr(match_stats, 'tackles', 0)
        self.interceptions += getattr(match_stats, 'interceptions', 0)
        self.blocks += getattr(match_stats, 'blocks', 0)
        self.clearances += getattr(match_stats, 'clearances', 0)
        self.aerial_duels_won += getattr(match_stats, 'aerial_duels_won', 0)
        self.aerial_duels_lost += getattr(match_stats, 'aerial_duels_lost', 0)
        self.offsides += getattr(match_stats, 'offsides', 0)

        self.saves += getattr(match_stats, 'saves', 0)
        self.saves_caught += getattr(match_stats, 'saves_caught', 0)
        self.saves_parried += getattr(match_stats, 'saves_parried', 0)
        self.punches += getattr(match_stats, 'punches', 0)
        self.one_on_one_saves += getattr(match_stats, 'one_on_one_saves', 0)
        self.high_claims += getattr(match_stats, 'high_claims', 0)
        self.goals_conceded += getattr(match_stats, 'goals_conceded', 0)
        self.clean_sheets += getattr(match_stats, 'clean_sheets', 0)

        self.yellow_cards += getattr(match_stats, 'yellow_cards', 0)
        self.red_cards += getattr(match_stats, 'red_cards', 0)
        self.own_goals += getattr(match_stats, 'own_goals', 0)

        rating = getattr(match_stats, 'match_rating', 6.0)
        if rating > 0:
            self.total_rating += rating
            self.avg_rating = self.total_rating / self.matches_played

    def get_pass_accuracy(self) -> float:
        """Get pass completion percentage."""
        if self.passes_attempted == 0:
            return 0.0
        return (self.passes_completed / self.passes_attempted) * 100

    def get_shot_accuracy(self) -> float:
        """Get shot on target percentage."""
        if self.shots == 0:
            return 0.0
        return (self.shots_on_target / self.shots) * 100

    def get_goals_per_90(self) -> float:
        """Get goals per 90 minutes."""
        if self.minutes_played == 0:
            return 0.0
        return (self.goals / self.minutes_played) * 90

    def get_assists_per_90(self) -> float:
        """Get assists per 90 minutes."""
        if self.minutes_played == 0:
            return 0.0
        return (self.assists / self.minutes_played) * 90


@dataclass
class TeamSeasonStats:
    """Accumulated statistics for a team over a season."""
    team_id: int
    team_name: str

    # Match results
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0

    # Goals
    goals_for: int = 0
    goals_against: int = 0

    # Shots
    shots: int = 0
    shots_on_target: int = 0

    # Possession
    total_possession: float = 0.0
    avg_possession: float = 0.0

    # Passing
    total_passes: int = 0

    # Other
    corners: int = 0
    fouls: int = 0

    def add_match(self, match_state: object, is_home: bool) -> None:
        """Add statistics from a match."""
        self.matches_played += 1

        if is_home:
            self.goals_for += match_state.home_score
            self.goals_against += match_state.away_score
            self.shots += match_state.home_shots
            self.shots_on_target += match_state.home_shots_on_target
            self.total_possession += match_state.home_possession
            self.total_passes += match_state.home_passes
            self.corners += match_state.home_corners
            self.fouls += match_state.home_fouls

            if match_state.home_score > match_state.away_score:
                self.wins += 1
            elif match_state.home_score == match_state.away_score:
                self.draws += 1
            else:
                self.losses += 1
        else:
            self.goals_for += match_state.away_score
            self.goals_against += match_state.home_score
            self.shots += match_state.away_shots
            self.shots_on_target += match_state.away_shots_on_target
            self.total_possession += (100 - match_state.home_possession)
            self.total_passes += match_state.away_passes
            self.corners += match_state.away_corners
            self.fouls += match_state.away_fouls

            if match_state.away_score > match_state.home_score:
                self.wins += 1
            elif match_state.away_score == match_state.home_score:
                self.draws += 1
            else:
                self.losses += 1

        self.avg_possession = self.total_possession / self.matches_played


class SeasonStatsTracker:
    """Track and aggregate statistics over a season."""

    def __init__(self):
        self.player_stats: Dict[int, PlayerSeasonStats] = {}
        self.team_stats: Dict[int, TeamSeasonStats] = {}
        self.match_history: List[Dict] = []

    def add_match(
        self,
        match_state: object,
        home_team_id: int,
        home_team_name: str,
        away_team_id: int,
        away_team_name: str,
    ) -> None:
        """Add a match to the season tracker."""
        # Record match
        self.match_history.append({
            "home_team": home_team_name,
            "away_team": away_team_name,
            "home_score": match_state.home_score,
            "away_score": match_state.away_score,
            "date": datetime.now().isoformat(),
        })

        # Update team stats
        if home_team_id not in self.team_stats:
            self.team_stats[home_team_id] = TeamSeasonStats(home_team_id, home_team_name)
        self.team_stats[home_team_id].add_match(match_state, is_home=True)

        if away_team_id not in self.team_stats:
            self.team_stats[away_team_id] = TeamSeasonStats(away_team_id, away_team_name)
        self.team_stats[away_team_id].add_match(match_state, is_home=False)

        # Update player stats
        for player_name, stats in match_state.home_player_stats.items():
            player_id = getattr(stats.player, 'id', None) or hash(player_name)
            position = getattr(stats.player, 'position', None)
            position_value = position.value if hasattr(position, 'value') else str(position) if position else None

            if player_id not in self.player_stats:
                self.player_stats[player_id] = PlayerSeasonStats(
                    player_id=player_id,
                    player_name=player_name,
                    team_id=home_team_id,
                    team_name=home_team_name,
                    position=position_value,
                )
            self.player_stats[player_id].add_match_stats(stats)

        for player_name, stats in match_state.away_player_stats.items():
            player_id = getattr(stats.player, 'id', None) or hash(player_name)
            position = getattr(stats.player, 'position', None)
            position_value = position.value if hasattr(position, 'value') else str(position) if position else None

            if player_id not in self.player_stats:
                self.player_stats[player_id] = PlayerSeasonStats(
                    player_id=player_id,
                    player_name=player_name,
                    team_id=away_team_id,
                    team_name=away_team_name,
                    position=position_value,
                )
            self.player_stats[player_id].add_match_stats(stats)

    def get_top_scorers(self, limit: int = 10) -> List[PlayerSeasonStats]:
        """Get top scorers."""
        return sorted(
            self.player_stats.values(),
            key=lambda x: (x.goals, x.avg_rating),
            reverse=True
        )[:limit]

    def get_top_assists(self, limit: int = 10) -> List[PlayerSeasonStats]:
        """Get top assist providers."""
        return sorted(
            self.player_stats.values(),
            key=lambda x: (x.assists, x.avg_rating),
            reverse=True
        )[:limit]

    def get_top_rated(self, limit: int = 10, min_matches: int = 5) -> List[PlayerSeasonStats]:
        """Get top rated players."""
        qualified = [p for p in self.player_stats.values() if p.matches_played >= min_matches]
        return sorted(
            qualified,
            key=lambda x: x.avg_rating,
            reverse=True
        )[:limit]

    def get_league_table(self) -> List[TeamSeasonStats]:
        """Get league table sorted by points."""
        return sorted(
            self.team_stats.values(),
            key=lambda x: (x.wins * 3 + x.draws, x.goals_for - x.goals_against, x.goals_for),
            reverse=True
        )


class MatchStatsExporter:
    """Export match statistics in various formats."""

    @staticmethod
    def export_to_json(
        match_state: object,
        output_path: Optional[Path] = None,
        include_players: bool = True,
    ) -> Dict[str, Any]:
        """
        Export match statistics to JSON format.

        Args:
            match_state: MatchState object
            output_path: Optional path to save JSON file
            include_players: Whether to include player-level statistics

        Returns:
            Dictionary containing match statistics
        """
        data = {
            "match_id": getattr(match_state, 'match_id', 0),
            "home_score": match_state.home_score,
            "away_score": match_state.away_score,
            "home_possession": match_state.home_possession,
            "away_possession": 100 - match_state.home_possession,
            "home_shots": match_state.home_shots,
            "away_shots": match_state.away_shots,
            "home_shots_on_target": match_state.home_shots_on_target,
            "away_shots_on_target": match_state.away_shots_on_target,
            "home_passes": match_state.home_passes,
            "away_passes": match_state.away_passes,
            "home_corners": match_state.home_corners,
            "away_corners": match_state.away_corners,
            "home_fouls": match_state.home_fouls,
            "away_fouls": match_state.away_fouls,
        }

        # Add new team stats if available
        for key in ['home_key_passes', 'away_key_passes', 'home_crosses', 'away_crosses',
                    'home_dribbles', 'away_dribbles', 'home_blocks', 'away_blocks',
                    'home_clearances', 'away_clearances', 'home_saves', 'away_saves']:
            if hasattr(match_state, key):
                data[key] = getattr(match_state, key)

        # Add player stats
        if include_players:
            data["home_players"] = {}
            for name, stats in match_state.home_player_stats.items():
                data["home_players"][name] = MatchStatsExporter._player_stats_to_dict(stats)

            data["away_players"] = {}
            for name, stats in match_state.away_player_stats.items():
                data["away_players"][name] = MatchStatsExporter._player_stats_to_dict(stats)

        # Add events
        if hasattr(match_state, 'events'):
            data["events"] = [
                {
                    "minute": e.minute,
                    "type": e.event_type.name if hasattr(e.event_type, 'name') else str(e.event_type),
                    "team": e.team,
                    "player": e.player,
                    "description": e.description,
                }
                for e in match_state.events
            ]

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)

        return data

    @staticmethod
    def _player_stats_to_dict(stats: object) -> Dict[str, Any]:
        """Convert player stats object to dictionary."""
        result = {}
        for key in ['minutes_played', 'passes_attempted', 'passes_completed', 'shots',
                    'shots_on_target', 'tackles', 'interceptions', 'fouls', 'goals',
                    'assists', 'key_passes', 'crosses', 'crosses_successful',
                    'dribbles', 'dribbles_failed', 'blocks', 'clearances',
                    'aerial_duels_won', 'aerial_duels_lost', 'saves',
                    'goals_conceded', 'yellow_cards', 'red_cards', 'match_rating']:
            if hasattr(stats, key):
                result[key] = getattr(stats, key)
        return result

    @staticmethod
    def export_team_stats_to_csv(
        season_tracker: SeasonStatsTracker,
        output_path: Path,
    ) -> None:
        """Export team statistics to CSV file."""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Team', 'Matches', 'Wins', 'Draws', 'Losses',
                'Goals For', 'Goals Against', 'Goal Difference',
                'Points', 'Shots', 'Shots on Target', 'Possession %',
            ])

            for team in season_tracker.get_league_table():
                gd = team.goals_for - team.goals_against
                points = team.wins * 3 + team.draws
                writer.writerow([
                    team.team_name, team.matches_played, team.wins, team.draws, team.losses,
                    team.goals_for, team.goals_against, gd,
                    points, team.shots, team.shots_on_target, f"{team.avg_possession:.1f}",
                ])

    @staticmethod
    def export_player_stats_to_csv(
        season_tracker: SeasonStatsTracker,
        output_path: Path,
        min_minutes: int = 90,
    ) -> None:
        """Export player statistics to CSV file."""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Player', 'Team', 'Position', 'Matches', 'Minutes',
                'Goals', 'Assists', 'Goals/90', 'Assists/90',
                'Shots', 'Shot Accuracy %', 'Key Passes',
                'Passes', 'Pass Accuracy %', 'Tackles',
                'Interceptions', 'Avg Rating',
            ])

            for player in sorted(
                season_tracker.player_stats.values(),
                key=lambda x: x.minutes_played,
                reverse=True
            ):
                if player.minutes_played < min_minutes:
                    continue

                writer.writerow([
                    player.player_name, player.team_name, player.position or 'N/A',
                    player.matches_played, player.minutes_played,
                    player.goals, player.assists, f"{player.get_goals_per_90():.2f}",
                    f"{player.get_assists_per_90():.2f}",
                    player.shots, f"{player.get_shot_accuracy():.1f}", player.key_passes,
                    player.passes_attempted, f"{player.get_pass_accuracy():.1f}",
                    player.tackles, player.interceptions, f"{player.avg_rating:.2f}",
                ])

    @staticmethod
    def export_leaderboards(
        season_tracker: SeasonStatsTracker,
        output_dir: Path,
    ) -> None:
        """Export all leaderboards to separate files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Top scorers
        with open(output_dir / 'top_scorers.json', 'w') as f:
            scorers = [
                {
                    'name': p.player_name,
                    'team': p.team_name,
                    'goals': p.goals,
                    'matches': p.matches_played,
                    'goals_per_90': p.get_goals_per_90(),
                }
                for p in season_tracker.get_top_scorers(20)
            ]
            json.dump(scorers, f, indent=2)

        # Top assists
        with open(output_dir / 'top_assists.json', 'w') as f:
            assists = [
                {
                    'name': p.player_name,
                    'team': p.team_name,
                    'assists': p.assists,
                    'matches': p.matches_played,
                    'assists_per_90': p.get_assists_per_90(),
                }
                for p in season_tracker.get_top_assists(20)
            ]
            json.dump(assists, f, indent=2)

        # Top rated
        with open(output_dir / 'top_rated.json', 'w') as f:
            rated = [
                {
                    'name': p.player_name,
                    'team': p.team_name,
                    'position': str(p.position) if p.position else 'N/A',
                    'avg_rating': p.avg_rating,
                    'matches': p.matches_played,
                }
                for p in season_tracker.get_top_rated(20)
            ]
            json.dump(rated, f, indent=2)

        # League table
        with open(output_dir / 'league_table.json', 'w') as f:
            table = [
                {
                    'name': t.team_name,
                    'matches': t.matches_played,
                    'wins': t.wins,
                    'draws': t.draws,
                    'losses': t.losses,
                    'goals_for': t.goals_for,
                    'goals_against': t.goals_against,
                    'goal_difference': t.goals_for - t.goals_against,
                    'points': t.wins * 3 + t.draws,
                }
                for t in season_tracker.get_league_table()
            ]
            json.dump(table, f, indent=2)
