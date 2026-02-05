"""Lightweight save/load system for nl_game_client.

This module provides save/load functionality for the natural language game client
that works with the cleaned data loader (non-database) approach.
"""

import json
import pickle
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any

from fm_manager.engine.calendar import Calendar, create_league_calendar, Match


class GameState:
    """Serializable game state for save/load."""

    def __init__(
        self,
        club_name: str,
        club_id: int,
        league_name: str,
        season_year: int,
        current_week: int,
        calendar_data: Dict[str, Any],
        in_game_date: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.club_name = club_name
        self.club_id = club_id
        self.league_name = league_name
        self.season_year = season_year
        self.current_week = current_week
        self.calendar_data = calendar_data
        self.in_game_date = in_game_date
        self.metadata = metadata or {}
        self.saved_at = datetime.now().isoformat()


class SaveLoadManager:
    """Manage game saves and loads for nl_game_client."""

    def __init__(self, save_dir: Optional[Path] = None):
        if save_dir is None:
            save_dir = Path.home() / ".fm_manager" / "saves"
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save_game(
        self,
        save_name: str,
        club_name: str,
        club_id: int,
        league_name: str,
        season_year: int,
        current_week: int,
        calendar: Calendar,
        in_game_date: date,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save current game state."""
        calendar_data = self._serialize_calendar(calendar)

        game_state = GameState(
            club_name=club_name,
            club_id=club_id,
            league_name=league_name,
            season_year=season_year,
            current_week=current_week,
            calendar_data=calendar_data,
            in_game_date=in_game_date.isoformat(),
            metadata=metadata,
        )

        save_path = self.save_dir / f"{save_name}.json"

        with open(save_path, "w") as f:
            json.dump(self._game_state_to_dict(game_state), f, indent=2)

        return str(save_path)

    def load_game(self, save_name: str) -> GameState:
        """Load game state from save file."""
        save_path = self.save_dir / f"{save_name}.json"

        if not save_path.exists():
            raise FileNotFoundError(f"Save file not found: {save_name}")

        with open(save_path, "r") as f:
            data = json.load(f)

        return self._dict_to_game_state(data)

    def restore_calendar(self, game_state: GameState) -> Calendar:
        """Restore calendar from game state."""
        return self._deserialize_calendar(game_state.calendar_data)

    def list_saves(self) -> list[Dict[str, Any]]:
        """List all available save files with metadata."""
        saves = []

        for save_path in sorted(
            self.save_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            try:
                with open(save_path, "r") as f:
                    data = json.load(f)

                saves.append(
                    {
                        "name": save_path.stem,
                        "club": data.get("club_name", "Unknown"),
                        "league": data.get("league_name", "Unknown"),
                        "week": data.get("current_week", 1),
                        "date": data.get("saved_at", "Unknown"),
                        "path": str(save_path),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

        return saves

    def delete_save(self, save_name: str) -> bool:
        """Delete a save file."""
        save_path = self.save_dir / f"{save_name}.json"

        if save_path.exists():
            save_path.unlink()
            return True
        return False

    def _serialize_calendar(self, calendar: Calendar) -> Dict[str, Any]:
        """Serialize calendar to dictionary."""
        return {
            "league_name": calendar.league_name,
            "season_year": calendar.season_year,
            "current_week": calendar.current_week,
            "matches": [
                {
                    "week": m.week,
                    "match_date": m.match_date.isoformat() if m.match_date else None,
                    "home_team": m.home_team,
                    "away_team": m.away_team,
                    "home_goals": m.home_goals,
                    "away_goals": m.away_goals,
                    "played": m.played,
                }
                for m in calendar.matches
            ],
        }

    def _deserialize_calendar(self, data: Dict[str, Any]) -> Calendar:
        """Deserialize calendar from dictionary."""
        calendar = create_league_calendar(
            data["league_name"],
            [],  # Teams will be extracted from matches
            data["season_year"],
        )
        calendar.current_week = data["current_week"]

        calendar.matches = []
        for m_data in data["matches"]:
            match_date = (
                date.fromisoformat(m_data["match_date"])
                if m_data.get("match_date")
                else date(2024, 8, 1)
            )
            match = Match(
                week=m_data["week"],
                match_date=match_date,
                home_team=m_data["home_team"],
                away_team=m_data["away_team"],
            )
            if m_data.get("played"):
                match.play(m_data["home_goals"], m_data["away_goals"])
            calendar.matches.append(match)

        return calendar

    def _game_state_to_dict(self, state: GameState) -> Dict[str, Any]:
        """Convert GameState to dictionary."""
        return {
            "club_name": state.club_name,
            "club_id": state.club_id,
            "league_name": state.league_name,
            "season_year": state.season_year,
            "current_week": state.current_week,
            "calendar_data": state.calendar_data,
            "in_game_date": state.in_game_date,
            "metadata": state.metadata,
            "saved_at": state.saved_at,
        }

    def _dict_to_game_state(self, data: Dict[str, Any]) -> GameState:
        """Convert dictionary to GameState."""
        return GameState(
            club_name=data["club_name"],
            club_id=data["club_id"],
            league_name=data["league_name"],
            season_year=data["season_year"],
            current_week=data["current_week"],
            calendar_data=data["calendar_data"],
            in_game_date=data["in_game_date"],
            metadata=data.get("metadata", {}),
        )


def format_save_info(save_info: Dict[str, Any]) -> str:
    """Format save info for display."""
    name = save_info["name"]
    club = save_info["club"]
    league = save_info["league"]
    week = save_info["week"]
    saved_at = save_info["date"]

    if isinstance(saved_at, str) and "T" in saved_at:
        try:
            dt = datetime.fromisoformat(saved_at)
            saved_at = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass

    return f"{name}: {club} ({league}) - Week {week} - Saved: {saved_at}"
