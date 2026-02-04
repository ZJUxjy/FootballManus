"""Save/Load system for game state persistence."""

import json
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as _Session
else:
    _Session = None  # type: ignore
from dataclasses import asdict

from sqlalchemy import select

from fm_manager.core.database import get_db_session
from fm_manager.core.models import Player, Club, League, Match, Transfer


class SaveGame:
    """Represents a save game file."""

    def __init__(
        self,
        save_name: str,
        save_date: datetime,
        current_season: int,
        current_week: int,
        player_club_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.save_name = save_name
        self.save_date = save_date
        self.current_season = current_season
        self.current_week = current_week
        self.player_club_id = player_club_id
        self.metadata = metadata or {}


class SaveLoadManager:
    """Manage game saves and loads."""

    def __init__(self, save_dir: Optional[Path] = None):
        if save_dir is None:
            save_dir = Path.home() / ".fm_manager" / "saves"
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def get_save_files(self) -> List[SaveGame]:
        """Get all available save files."""
        saves = []

        if not self.save_dir.exists():
            return saves

        for save_path in self.save_dir.glob("*.json"):
            try:
                with open(save_path, 'r') as f:
                    data = json.load(f)

                saves.append(SaveGame(
                    save_name=data.get("save_name", save_path.stem),
                    save_date=datetime.fromisoformat(data.get("save_date", "")),
                    current_season=data.get("current_season", 1),
                    current_week=data.get("current_week", 1),
                    player_club_id=data.get("player_club_id"),
                    metadata=data.get("metadata", {}),
                ))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return sorted(saves, key=lambda s: s.save_date, reverse=True)

    def save_game(
        self,
        session,  # type: ignore
        save_name: str,
        current_season: int = 1,
        current_week: int = 1,
        player_club_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save current game state to a JSON file."""
        save_data = {
            "save_name": save_name,
            "save_date": datetime.now().isoformat(),
            "current_season": current_season,
            "current_week": current_week,
            "player_club_id": player_club_id,
            "metadata": metadata or {},
            "game_state": self._capture_game_state(session),
        }

        save_path = self.save_dir / f"{save_name}.json"

        with open(save_path, 'w') as f:
            json.dump(save_data, f, indent=2, default=str)

        return str(save_path)

    def load_game(self, save_name: str) -> Dict[str, Any]:
        """Load game state from a save file."""
        save_path = self.save_dir / f"{save_name}.json"

        if not save_path.exists():
            raise FileNotFoundError(f"Save file not found: {save_name}")

        with open(save_path, 'r') as f:
            return json.load(f)

    def delete_save(self, save_name: str) -> bool:
        """Delete a save file."""
        save_path = self.save_dir / f"{save_name}.json"

        if save_path.exists():
            save_path.unlink()
            return True
        return False

    def _capture_game_state(self, session: "Session") -> Dict[str, Any]:  # type: ignore
        """Capture current game state from database."""
        state = {
            "clubs": [],
            "players": [],
            "leagues": [],
            "matches": [],
            "transfers": [],
        }

        # Export clubs
        clubs = session.execute(select(Club)).scalars().all()
        for club in clubs:
            state["clubs"].append({
                "id": club.id,
                "name": club.name,
                "league_id": club.league_id,
                "budget": club.budget,
                "wage_bill": club.wage_bill,
                "reputation": club.reputation,
            })

        # Export players
        players = session.execute(select(Player)).scalars().all()
        for player in players:
            state["players"].append({
                "id": player.id,
                "first_name": player.first_name,
                "last_name": player.last_name,
                "birth_date": player.birth_date.isoformat() if player.birth_date else None,
                "nationality": player.nationality,
                "position": player.position.value if player.position else None,
                "club_id": player.club_id,
                "current_ability": player.current_ability,
                "potential_ability": player.potential_ability,
                "fitness": player.fitness,
                "morale": player.morale,
                "form": player.form,
                "salary": player.salary,
                "market_value": player.market_value,
                "contract_until": player.contract_until.isoformat() if player.contract_until else None,
                "appearances": player.appearances,
                "goals": player.goals,
                "assists": player.assists,
                "career_goals": player.career_goals,
                "career_appearances": player.career_appearances,
            })

        # Export leagues
        leagues = session.execute(select(League)).scalars().all()
        for league in leagues:
            state["leagues"].append({
                "id": league.id,
                "name": league.name,
                "country": league.country,
                "tier": league.tier,
                "season": league.season,
            })

        # Export recent matches (last 100)
        matches = session.execute(
            select(Match).order_by(Match.date.desc()).limit(100)
        ).scalars().all()

        for match in matches:
            state["matches"].append({
                "id": match.id,
                "home_club_id": match.home_club_id,
                "away_club_id": match.away_club_id,
                "league_id": match.league_id,
                "home_score": match.home_score,
                "away_score": match.away_score,
                "date": match.date.isoformat() if match.date else None,
                "week": match.week,
                "season": match.season,
            })

        # Export recent transfers (last 50)
        transfers = session.execute(
            select(Transfer).order_by(Transfer.date.desc()).limit(50)
        ).scalars().all()

        for transfer in transfers:
            state["transfers"].append({
                "id": transfer.id,
                "player_id": transfer.player_id,
                "from_club_id": transfer.from_club_id,
                "to_club_id": transfer.to_club_id,
                "fee": transfer.fee,
                "date": transfer.date.isoformat() if transfer.date else None,
                "transfer_type": transfer.transfer_type,
            })

        return state

    def create_quick_save(
        self,
        session,  # type: ignore
        current_season: int = 1,
        current_week: int = 1,
        player_club_id: Optional[int] = None,
    ) -> str:
        """Create a quick save (autosave)."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_name = f"autosave_{timestamp}"
        return self.save_game(session, save_name, current_season, current_week, player_club_id)

    def get_autosaves(self, max_count: int = 5) -> List[SaveGame]:
        """Get the most recent autosaves."""
        all_saves = self.get_save_files()
        autosaves = [s for s in all_saves if s.save_name.startswith("autosave_")]
        return autosaves[:max_count]
