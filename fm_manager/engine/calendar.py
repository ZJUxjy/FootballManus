"""Simple Calendar System for FM Manager.

Provides basic match scheduling for a single league season.
- 38 rounds for Premier League style
- 34 rounds for Bundesliga style
- Weekly matches (weekends)
- Simple round-robin scheduling
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Tuple, Dict
import random


@dataclass
class Match:
    """A single match in the calendar."""

    week: int
    match_date: date
    home_team: str
    away_team: str
    played: bool = False
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None

    @property
    def result_str(self) -> str:
        """Get result as string."""
        if not self.played:
            return "vs"
        return f"{self.home_goals}-{self.away_goals}"

    def play(self, home_goals: int, away_goals: int):
        """Record match result."""
        self.home_goals = home_goals
        self.away_goals = away_goals
        self.played = True


@dataclass
class Calendar:
    """Simple season calendar for league matches."""

    season_year: int
    league_name: str
    teams: List[str]
    current_week: int = 1
    matches: List[Match] = field(default_factory=list)

    def __post_init__(self):
        """Generate fixtures if not provided."""
        if not self.matches:
            self.matches = self._generate_fixtures()

    def _generate_fixtures(self) -> List[Match]:
        """Generate round-robin fixtures."""
        n = len(self.teams)
        if n % 2 == 1:
            # Add a bye if odd number of teams
            teams = self.teams + ["BYE"]
            n += 1
        else:
            teams = self.teams[:]

        matches = []

        # Generate first half (home and away)
        for round_num in range(n - 1):
            round_matches = []
            for i in range(n // 2):
                home = teams[i]
                away = teams[n - 1 - i]
                if home != "BYE" and away != "BYE":
                    round_matches.append((home, away))

            # Rotate teams (keep first team fixed)
            teams = [teams[0]] + [teams[-1]] + teams[1:-1]

            # Schedule this round
            match_date = self._get_match_date(round_num + 1)
            for idx, (home, away) in enumerate(round_matches):
                matches.append(
                    Match(week=round_num + 1, match_date=match_date, home_team=home, away_team=away)
                )

        # Generate second half (reverse fixtures)
        num_rounds = n - 1
        for round_num in range(num_rounds):
            round_matches = []
            for i in range(n // 2):
                home = teams[n - 1 - i]  # Swap home/away
                away = teams[i]
                if home != "BYE" and away != "BYE":
                    round_matches.append((home, away))

            teams = [teams[0]] + [teams[-1]] + teams[1:-1]

            match_date = self._get_match_date(num_rounds + round_num + 1)
            for idx, (home, away) in enumerate(round_matches):
                matches.append(
                    Match(
                        week=num_rounds + round_num + 1,
                        match_date=match_date,
                        home_team=home,
                        away_team=away,
                    )
                )

        return matches

    def _get_match_date(self, week: int) -> date:
        """Calculate match date for a given week."""
        # Season starts first weekend of August
        start_date = date(self.season_year, 8, 1)
        # Find first Saturday
        while start_date.weekday() != 5:  # 5 = Saturday
            start_date += timedelta(days=1)

        # Each week is 7 days
        return start_date + timedelta(weeks=week - 1)

    def get_current_matches(self) -> List[Match]:
        """Get matches for current week."""
        return [m for m in self.matches if m.week == self.current_week]

    def get_team_matches(self, team_name: str) -> List[Match]:
        """Get all matches for a specific team."""
        return [m for m in self.matches if m.home_team == team_name or m.away_team == team_name]

    def get_next_unplayed_match(self, team_name: str) -> Optional[Match]:
        """Get next unplayed match for a team."""
        team_matches = self.get_team_matches(team_name)
        unplayed = [m for m in team_matches if not m.played]
        if unplayed:
            return min(unplayed, key=lambda m: m.week)
        return None

    def advance_week(self) -> bool:
        """Advance to next week. Returns False if season ended."""
        max_week = max(m.week for m in self.matches)
        if self.current_week < max_week:
            self.current_week += 1
            return True
        return False

    def get_standings(self) -> Dict[str, Dict]:
        """Calculate league standings."""
        standings = {
            team: {
                "played": 0,
                "won": 0,
                "drawn": 0,
                "lost": 0,
                "gf": 0,
                "ga": 0,
                "gd": 0,
                "points": 0,
            }
            for team in self.teams
        }

        for match in self.matches:
            if not match.played:
                continue

            home = match.home_team
            away = match.away_team
            hg = match.home_goals
            ag = match.away_goals

            # Update played
            standings[home]["played"] += 1
            standings[away]["played"] += 1

            # Update goals
            standings[home]["gf"] += hg
            standings[home]["ga"] += ag
            standings[away]["gf"] += ag
            standings[away]["ga"] += hg

            # Update results
            if hg > ag:
                standings[home]["won"] += 1
                standings[home]["points"] += 3
                standings[away]["lost"] += 1
            elif hg < ag:
                standings[away]["won"] += 1
                standings[away]["points"] += 3
                standings[home]["lost"] += 1
            else:
                standings[home]["drawn"] += 1
                standings[home]["points"] += 1
                standings[away]["drawn"] += 1
                standings[away]["points"] += 1

        # Calculate goal difference
        for team in standings:
            standings[team]["gd"] = standings[team]["gf"] - standings[team]["ga"]

        return standings

    def get_season_progress(self) -> Tuple[int, int]:
        """Get season progress (played matches, total matches)."""
        played = sum(1 for m in self.matches if m.played)
        total = len(self.matches)
        return played, total

    def is_season_complete(self) -> bool:
        """Check if all matches have been played."""
        return all(m.played for m in self.matches)


def create_league_calendar(league_name: str, teams: List[str], season_year: int = 2024) -> Calendar:
    """Create a calendar for a league season.

    Args:
        league_name: Name of the league
        teams: List of team names
        season_year: Starting year of season

    Returns:
        Calendar object with generated fixtures
    """
    return Calendar(season_year=season_year, league_name=league_name, teams=teams)


# Example usage
if __name__ == "__main__":
    # Create a simple 4-team league for testing
    teams = ["Arsenal", "Chelsea", "Liverpool", "Man City"]
    calendar = create_league_calendar("Test League", teams, 2024)

    print(f"Calendar for {calendar.league_name} {calendar.season_year}")
    print(f"Teams: {', '.join(calendar.teams)}")
    print(f"Total matches: {len(calendar.matches)}")
    print()

    # Show first 3 rounds
    print("First 3 rounds:")
    for week in range(1, 4):
        print(f"\nWeek {week} ({calendar._get_match_date(week)}):")
        matches = [m for m in calendar.matches if m.week == week]
        for m in matches:
            print(f"  {m.home_team} vs {m.away_team}")

    print("\n" + "=" * 50)
    print("Simulating some matches...")

    # Simulate first week
    for match in calendar.get_current_matches():
        match.play(random.randint(0, 3), random.randint(0, 3))

    calendar.advance_week()

    # Show standings
    standings = calendar.get_standings()
    print("\nStandings after Week 1:")
    sorted_teams = sorted(
        standings.items(), key=lambda x: (x[1]["points"], x[1]["gd"]), reverse=True
    )
    for pos, (team, stats) in enumerate(sorted_teams, 1):
        print(
            f"{pos}. {team}: {stats['points']}pts "
            f"({stats['won']}W {stats['drawn']}D {stats['lost']}L) "
            f"GD:{stats['gd']:+d}"
        )
