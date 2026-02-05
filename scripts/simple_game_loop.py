"""Simple Game Loop with Calendar Integration.

This provides a basic playable season loop using the new calendar system.
"""

import asyncio
import random
from datetime import date
from typing import Optional

from fm_manager.engine.calendar import Calendar, create_league_calendar, Match
from fm_manager.engine.match_engine_markov import EnhancedMarkovEngine
from fm_manager.data.cleaned_data_loader import load_for_match_engine, ClubDataFull


class SimpleGameLoop:
    """Simple game loop for playing through a season."""

    def __init__(self, club: ClubDataFull, season_year: int = 2024):
        """Initialize game loop."""
        self.club = club
        self.season_year = season_year

        # Create calendar for the league
        # Get all clubs in the same league
        clubs, _ = load_for_match_engine()
        league_clubs = [c for c in clubs.values() if c.league == club.league]

        if len(league_clubs) < 2:
            # Fallback: create mini league with current club
            league_clubs = [club, clubs[list(clubs.keys())[0]]]

        team_names = [c.name for c in league_clubs[:20]]  # Max 20 teams

        self.calendar = create_league_calendar(club.league, team_names, season_year)

        # Initialize match engine
        self.match_engine = EnhancedMarkovEngine()

        # Game state
        self.current_date = date(season_year, 8, 1)

    def get_user_matches(self) -> list[Match]:
        """Get matches involving user's club for current week."""
        return [
            m
            for m in self.calendar.get_current_matches()
            if m.home_team == self.club.name or m.away_team == self.club.name
        ]

    def simulate_week(self) -> list[dict]:
        """Simulate all matches for current week using Markov match engine."""
        results = []
        clubs, _ = load_for_match_engine()

        for match in self.calendar.get_current_matches():
            home_club = clubs.get(match.home_team)
            away_club = clubs.get(match.away_team)

            if home_club and away_club:
                match_result = self.match_engine.simulate(home_club.players, away_club.players)
                home_goals = match_result.home_goals
                away_goals = match_result.away_goals
            else:
                home_goals = random.randint(0, 4)
                away_goals = random.randint(0, 3)

            match.play(home_goals, away_goals)

            results.append(
                {
                    "home": match.home_team,
                    "away": match.away_team,
                    "score": f"{home_goals}-{away_goals}",
                    "is_user_team": (
                        match.home_team == self.club.name or match.away_team == self.club.name
                    ),
                }
            )

        return results

    def get_standings_table(self) -> str:
        """Get formatted standings table."""
        standings = self.calendar.get_standings()

        # Sort by points, then goal difference
        sorted_teams = sorted(
            standings.items(), key=lambda x: (x[1]["points"], x[1]["gd"]), reverse=True
        )

        lines = ["\n📊 LEAGUE TABLE\n" + "=" * 70]
        lines.append(
            f"{'Pos':<5} {'Team':<25} {'P':<4} {'W':<4} {'D':<4} {'L':<4} {'GF':<4} {'GA':<4} {'GD':<5} {'Pts':<5}"
        )
        lines.append("-" * 70)

        for pos, (team, stats) in enumerate(sorted_teams, 1):
            marker = " 👤" if team == self.club.name else ""
            lines.append(
                f"{pos:<5} {team + marker:<25} {stats['played']:<4} "
                f"{stats['won']:<4} {stats['drawn']:<4} {stats['lost']:<4} "
                f"{stats['gf']:<4} {stats['ga']:<4} {stats['gd']:<+5} {stats['points']:<5}"
            )

        return "\n".join(lines)

    def play_week(self) -> bool:
        """Play current week and advance. Returns False if season ended."""
        # Get current week info
        week = self.calendar.current_week
        match_date = self.calendar._get_match_date(week)

        print(f"\n{'=' * 70}")
        print(f"📅 WEEK {week} - {match_date.strftime('%B %d, %Y')}")
        print(f"{'=' * 70}")

        # Show user's upcoming match
        user_matches = self.get_user_matches()
        if user_matches:
            match = user_matches[0]
            if match.home_team == self.club.name:
                print(f"🏟️  Upcoming: {match.home_team} vs {match.away_team} (Home)")
            else:
                print(f"✈️  Upcoming: {match.away_team} vs {match.home_team} (Away)")

        input("\nPress Enter to simulate week...")

        # Simulate all matches
        results = self.simulate_week()

        # Show results
        print("\n📋 MATCH RESULTS:")
        print("-" * 70)
        for result in results:
            marker = " 👤" if result["is_user_team"] else ""
            print(f"  {result['home']} {result['score']} {result['away']}{marker}")

        # Show standings
        print(self.get_standings_table())

        # Advance to next week
        has_more = self.calendar.advance_week()

        if not has_more:
            print("\n" + "=" * 70)
            print("🏆 SEASON COMPLETE!")
            print("=" * 70)
            self.show_final_standings()
            return False

        return True

    def show_final_standings(self):
        """Show final season standings."""
        standings = self.calendar.get_standings()
        sorted_teams = sorted(
            standings.items(), key=lambda x: (x[1]["points"], x[1]["gd"]), reverse=True
        )

        # Find user's position
        user_pos = None
        for pos, (team, _) in enumerate(sorted_teams, 1):
            if team == self.club.name:
                user_pos = pos
                break

        print(f"\nFinal Position: {user_pos}/{len(sorted_teams)}")

        # Show top 5
        print("\nTop 5:")
        for pos, (team, stats) in enumerate(sorted_teams[:5], 1):
            marker = " 👤" if team == self.club.name else ""
            print(f"  {pos}. {team}{marker} - {stats['points']}pts")

    async def run_season(self):
        """Run full season."""
        print("\n" + "=" * 70)
        print(f"🏆 {self.club.league} {self.season_year}-{self.season_year + 1}")
        print(f"👤 Managing: {self.club.name}")
        print("=" * 70)

        print(f"\n📅 Season starts: August 2024")
        print(f"📅 Season ends: May 2025")
        print(f"⚽ Total matchdays: {max(m.week for m in self.calendar.matches)}")

        input("\nPress Enter to start season...")

        # Play through all weeks
        while True:
            try:
                has_more = self.play_week()
                if not has_more:
                    break
            except KeyboardInterrupt:
                print("\n\nSeason paused. You can resume later.")
                break


async def main():
    """Run simple game loop."""
    # Load a club
    clubs, _ = load_for_match_engine()

    # Find a Premier League club with players
    for club in clubs.values():
        if "La Liga" == club.league and len(getattr(club, "players", [])) > 10:
            print(f"Selected club: {club.name}")
            break
    else:
        club = list(clubs.values())[0]

    # Create and run game loop
    game = SimpleGameLoop(club)
    await game.run_season()


if __name__ == "__main__":
    asyncio.run(main())
