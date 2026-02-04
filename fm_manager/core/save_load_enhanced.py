"""Enhanced Save/Load System for FM Manager.

Features:
- Compressed save files (gzip)
- JSON-based serialization
- Version control for save compatibility
- Auto-save functionality
- Save file metadata and thumbnails
- Cloud save support (optional)
"""

import gzip
import json
import hashlib
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from fm_manager.core.database import get_db_session
from fm_manager.core.models import (
    Player,
    Club,
    League,
    Match,
    Transfer,
    Season,
    CupCompetition,
    CupEdition,
    CupRound,
    CupParticipant,
    CupMatch,
)


class SaveVersion(Enum):
    """Save file version for compatibility."""

    V1_0 = "1.0"  # Initial version
    V1_1 = "1.1"  # Added cup competitions
    V1_2 = "1.2"  # Added player development tracking
    CURRENT = V1_2


@dataclass
class SaveMetadata:
    """Metadata for a save game."""

    save_name: str
    save_date: datetime
    version: str
    current_season: int
    current_week: int
    player_club_id: Optional[int]
    player_club_name: Optional[str]
    in_game_date: Optional[date]
    play_time_minutes: int = 0
    total_matches_played: int = 0
    total_goals_scored: int = 0
    league_position: Optional[int] = None
    thumbnail_data: Optional[str] = None  # Base64 encoded mini screenshot

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "save_name": self.save_name,
            "save_date": self.save_date.isoformat(),
            "version": self.version,
            "current_season": self.current_season,
            "current_week": self.current_week,
            "player_club_id": self.player_club_id,
            "player_club_name": self.player_club_name,
            "in_game_date": self.in_game_date.isoformat() if self.in_game_date else None,
            "play_time_minutes": self.play_time_minutes,
            "total_matches_played": self.total_matches_played,
            "total_goals_scored": self.total_goals_scored,
            "league_position": self.league_position,
            "thumbnail_data": self.thumbnail_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SaveMetadata":
        """Create from dictionary."""
        return cls(
            save_name=data["save_name"],
            save_date=datetime.fromisoformat(data["save_date"]),
            version=data.get("version", "1.0"),
            current_season=data.get("current_season", 1),
            current_week=data.get("current_week", 1),
            player_club_id=data.get("player_club_id"),
            player_club_name=data.get("player_club_name"),
            in_game_date=date.fromisoformat(data["in_game_date"])
            if data.get("in_game_date")
            else None,
            play_time_minutes=data.get("play_time_minutes", 0),
            total_matches_played=data.get("total_matches_played", 0),
            total_goals_scored=data.get("total_goals_scored", 0),
            league_position=data.get("league_position"),
            thumbnail_data=data.get("thumbnail_data"),
        )


class GameState:
    """Complete game state for save/load."""

    def __init__(self):
        self.clubs: List[Dict] = []
        self.players: List[Dict] = []
        self.leagues: List[Dict] = []
        self.matches: List[Dict] = []
        self.transfers: List[Dict] = []
        self.seasons: List[Dict] = []
        self.cup_competitions: List[Dict] = []
        self.cup_editions: List[Dict] = []
        self.cup_rounds: List[Dict] = []
        self.cup_participants: List[Dict] = []
        self.cup_matches: List[Dict] = []
        self.game_settings: Dict[str, Any] = {}
        self.achievements: List[Dict] = []
        self.statistics: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "clubs": self.clubs,
            "players": self.players,
            "leagues": self.leagues,
            "matches": self.matches,
            "transfers": self.transfers,
            "seasons": self.seasons,
            "cup_competitions": self.cup_competitions,
            "cup_editions": self.cup_editions,
            "cup_rounds": self.cup_rounds,
            "cup_participants": self.cup_participants,
            "cup_matches": self.cup_matches,
            "game_settings": self.game_settings,
            "achievements": self.achievements,
            "statistics": self.statistics,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameState":
        """Create from dictionary."""
        state = cls()
        state.clubs = data.get("clubs", [])
        state.players = data.get("players", [])
        state.leagues = data.get("leagues", [])
        state.matches = data.get("matches", [])
        state.transfers = data.get("transfers", [])
        state.seasons = data.get("seasons", [])
        state.cup_competitions = data.get("cup_competitions", [])
        state.cup_editions = data.get("cup_editions", [])
        state.cup_rounds = data.get("cup_rounds", [])
        state.cup_participants = data.get("cup_participants", [])
        state.cup_matches = data.get("cup_matches", [])
        state.game_settings = data.get("game_settings", {})
        state.achievements = data.get("achievements", [])
        state.statistics = data.get("statistics", {})
        return state


class EnhancedSaveLoadManager:
    """Enhanced save/load manager with compression and auto-save."""

    SAVE_EXTENSION = ".fmsave"  # FM Manager Save
    AUTO_SAVE_PREFIX = "autosave_"
    MAX_AUTO_SAVES = 5

    def __init__(self, save_dir: Optional[Path] = None):
        if save_dir is None:
            save_dir = Path.home() / ".fm_manager" / "saves"
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # Auto-save settings
        self.auto_save_enabled = True
        self.auto_save_interval_minutes = 15
        self._auto_save_thread: Optional[threading.Thread] = None
        self._stop_auto_save = threading.Event()

        # Current game session
        self._session_start_time: Optional[datetime] = None
        self._current_save_name: Optional[str] = None

    def start_session(self, save_name: Optional[str] = None):
        """Start a new game session."""
        self._session_start_time = datetime.now()
        self._current_save_name = save_name

        if self.auto_save_enabled:
            self._start_auto_save()

    def end_session(self):
        """End current game session."""
        self._stop_auto_save.set()
        if self._auto_save_thread and self._auto_save_thread.is_alive():
            self._auto_save_thread.join(timeout=5)

    def _start_auto_save(self):
        """Start auto-save background thread."""

        def auto_save_worker():
            while not self._stop_auto_save.wait(self.auto_save_interval_minutes * 60):
                if self._current_save_name:
                    try:
                        # Auto-save requires session - disabled for now
                        # self.create_auto_save(session)
                        pass
                    except Exception as e:
                        print(f"Auto-save failed: {e}")

        self._stop_auto_save.clear()
        self._auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
        self._auto_save_thread.start()

    def create_auto_save(self, session: Session) -> str:
        """Create an auto-save."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_name = f"{self.AUTO_SAVE_PREFIX}{timestamp}"

        # Clean up old auto-saves
        self._cleanup_auto_saves()

        return self.save_game(session=session, save_name=save_name, is_auto_save=True)

    def _cleanup_auto_saves(self):
        """Remove old auto-saves, keeping only the most recent ones."""
        auto_saves = sorted(
            self.save_dir.glob(f"{self.AUTO_SAVE_PREFIX}*{self.SAVE_EXTENSION}"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for old_save in auto_saves[self.MAX_AUTO_SAVES :]:
            old_save.unlink()

    def get_save_files(self) -> List[Tuple[SaveMetadata, Path]]:
        """Get all available save files with metadata."""
        saves = []

        if not self.save_dir.exists():
            return saves

        for save_path in self.save_dir.glob(f"*{self.SAVE_EXTENSION}"):
            try:
                metadata = self._read_save_metadata(save_path)
                if metadata:
                    saves.append((metadata, save_path))
            except Exception:
                continue

        # Sort by save date (newest first)
        saves.sort(key=lambda x: x[0].save_date, reverse=True)
        return saves

    def _read_save_metadata(self, save_path: Path) -> Optional[SaveMetadata]:
        """Read metadata from a save file."""
        try:
            with gzip.open(save_path, "rt", encoding="utf-8") as f:
                data = json.load(f)

            return SaveMetadata.from_dict(data.get("metadata", {}))
        except Exception:
            return None

    def save_game(
        self,
        session: Session,
        save_name: str,
        current_season: int = 1,
        current_week: int = 1,
        player_club_id: Optional[int] = None,
        in_game_date: Optional[date] = None,
        is_auto_save: bool = False,
    ) -> str:
        """Save current game state to a compressed file."""
        # Generate metadata
        player_club_name = None
        if player_club_id:
            club = session.get(Club, player_club_id)
            if club:
                player_club_name = club.name

        # Calculate play time
        play_time = 0
        if self._session_start_time:
            play_time = int((datetime.now() - self._session_start_time).total_seconds() / 60)

        # Get statistics
        stats = self._calculate_statistics(session, player_club_id)

        metadata = SaveMetadata(
            save_name=save_name,
            save_date=datetime.now(),
            version=SaveVersion.CURRENT.value,
            current_season=current_season,
            current_week=current_week,
            player_club_id=player_club_id,
            player_club_name=player_club_name,
            in_game_date=in_game_date,
            play_time_minutes=play_time,
            total_matches_played=stats.get("matches_played", 0),
            total_goals_scored=stats.get("goals_scored", 0),
            league_position=stats.get("league_position"),
        )

        # Capture game state
        game_state = self._capture_game_state(session)

        # Build save data
        save_data = {
            "metadata": metadata.to_dict(),
            "game_state": game_state.to_dict(),
            "checksum": "",  # Will be calculated
        }

        # Calculate checksum for integrity
        checksum_data = json.dumps(save_data["game_state"], sort_keys=True)
        save_data["checksum"] = hashlib.sha256(checksum_data.encode()).hexdigest()

        # Save to file with compression
        save_path = self.save_dir / f"{save_name}{self.SAVE_EXTENSION}"

        with gzip.open(save_path, "wt", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, default=str)

        return str(save_path)

    async def save_game_async(
        self,
        session: AsyncSession,
        save_name: str,
        current_season: int = 1,
        current_week: int = 1,
        player_club_id: Optional[int] = None,
        in_game_date: Optional[date] = None,
        is_auto_save: bool = False,
    ) -> str:
        """Save current game state to a compressed file (async version)."""
        # Generate metadata
        player_club_name = None
        if player_club_id:
            result = await session.execute(select(Club).where(Club.id == player_club_id))
            club = result.scalar_one_or_none()
            if club:
                player_club_name = club.name

        # Calculate play time
        play_time = 0
        if self._session_start_time:
            play_time = int((datetime.now() - self._session_start_time).total_seconds() / 60)

        # Get statistics
        stats = await self._calculate_statistics_async(session, player_club_id)

        metadata = SaveMetadata(
            save_name=save_name,
            save_date=datetime.now(),
            version=SaveVersion.CURRENT.value,
            current_season=current_season,
            current_week=current_week,
            player_club_id=player_club_id,
            player_club_name=player_club_name,
            in_game_date=in_game_date,
            play_time_minutes=play_time,
            total_matches_played=stats.get("matches_played", 0),
            total_goals_scored=stats.get("goals_scored", 0),
            league_position=stats.get("league_position"),
        )

        # Capture game state
        game_state = await self._capture_game_state_async(session)

        # Build save data
        save_data = {
            "metadata": metadata.to_dict(),
            "game_state": game_state.to_dict(),
            "checksum": "",  # Will be calculated
        }

        # Calculate checksum for integrity
        checksum_data = json.dumps(save_data["game_state"], sort_keys=True)
        save_data["checksum"] = hashlib.sha256(checksum_data.encode()).hexdigest()

        # Save to file with compression
        save_path = self.save_dir / f"{save_name}{self.SAVE_EXTENSION}"

        with gzip.open(save_path, "wt", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, default=str)

        return str(save_path)

    def load_game(self, save_name: str) -> Tuple[SaveMetadata, GameState]:
        """Load game state from a save file."""
        save_path = self.save_dir / f"{save_name}{self.SAVE_EXTENSION}"

        if not save_path.exists():
            raise FileNotFoundError(f"Save file not found: {save_name}")

        # Read and decompress
        with gzip.open(save_path, "rt", encoding="utf-8") as f:
            save_data = json.load(f)

        # Verify checksum
        stored_checksum = save_data.get("checksum", "")
        game_state_data = save_data.get("game_state", {})
        calculated_checksum = hashlib.sha256(
            json.dumps(game_state_data, sort_keys=True).encode()
        ).hexdigest()

        if stored_checksum != calculated_checksum:
            raise ValueError("Save file is corrupted (checksum mismatch)")

        # Parse data
        metadata = SaveMetadata.from_dict(save_data["metadata"])
        game_state = GameState.from_dict(game_state_data)

        # Check version compatibility
        if metadata.version != SaveVersion.CURRENT.value:
            game_state = self._migrate_save(game_state, metadata.version)

        return metadata, game_state

    def _migrate_save(self, game_state: GameState, from_version: str) -> GameState:
        """Migrate save from older version to current."""
        # Add migration logic here as versions change
        if from_version == "1.0":
            # Migrate from 1.0 to 1.1
            pass

        if from_version in ["1.0", "1.1"]:
            # Migrate to 1.2
            pass

        return game_state

    def restore_game_state(self, session: Session, game_state: GameState):
        """Restore game state to database."""
        # Clear existing data (optional - depends on strategy)
        # session.execute(text("DELETE FROM cup_matches"))
        # session.execute(text("DELETE FROM cup_participants"))
        # ... etc

        # Restore clubs
        for club_data in game_state.clubs:
            club = Club(**club_data)
            session.merge(club)

        # Restore players
        for player_data in game_state.players:
            # Convert position string back to enum
            if player_data.get("position"):
                from fm_manager.core.models.player import Position

                try:
                    player_data["position"] = Position(player_data["position"])
                except ValueError:
                    player_data["position"] = None

            # Parse dates
            if player_data.get("birth_date"):
                player_data["birth_date"] = date.fromisoformat(player_data["birth_date"])
            if player_data.get("contract_until"):
                player_data["contract_until"] = date.fromisoformat(player_data["contract_until"])

            player = Player(**player_data)
            session.merge(player)

        # Restore other entities...
        # (Similar pattern for leagues, matches, transfers, etc.)

        session.commit()

    async def restore_game_state_async(self, session: AsyncSession, game_state: GameState):
        """Restore game state to database (async version)."""
        from fm_manager.core.models.player import Position, Foot

        # Restore clubs - skip if data issues
        for club_data in game_state.clubs:
            try:
                # Handle reputation_level enum if present as string
                if club_data.get("reputation_level"):
                    from fm_manager.core.models.club import ClubReputation

                    rep_val = club_data["reputation_level"]
                    if isinstance(rep_val, str):
                        try:
                            club_data["reputation_level"] = ClubReputation[
                                rep_val.upper().replace(" ", "_")
                            ]
                        except KeyError:
                            club_data["reputation_level"] = ClubReputation.RESPECTABLE

                club = Club(**club_data)
                await session.merge(club)
            except Exception as e:
                # Skip clubs that can't be restored
                print(f"Warning: Could not restore club {club_data.get('name', 'Unknown')}: {e}")
                continue

        # Restore players - handle enum conversions carefully
        for player_data in game_state.players:
            try:
                # Convert position string back to enum
                if player_data.get("position"):
                    try:
                        player_data["position"] = Position(player_data["position"])
                    except ValueError:
                        player_data["position"] = None

                # Convert preferred_foot string back to enum
                if player_data.get("preferred_foot"):
                    foot_val = player_data["preferred_foot"]
                    if isinstance(foot_val, str):
                        try:
                            # Try direct enum creation first
                            player_data["preferred_foot"] = Foot(foot_val)
                        except ValueError:
                            # Try by name (RIGHT, LEFT, BOTH)
                            try:
                                player_data["preferred_foot"] = Foot[foot_val.upper()]
                            except KeyError:
                                player_data["preferred_foot"] = Foot.RIGHT

                # Convert secondary_position string back to enum
                if player_data.get("secondary_position"):
                    try:
                        player_data["secondary_position"] = Position(
                            player_data["secondary_position"]
                        )
                    except ValueError:
                        player_data["secondary_position"] = None

                # Parse dates
                if player_data.get("birth_date"):
                    player_data["birth_date"] = date.fromisoformat(player_data["birth_date"])
                if player_data.get("contract_until"):
                    player_data["contract_until"] = date.fromisoformat(
                        player_data["contract_until"]
                    )

                player = Player(**player_data)
                await session.merge(player)
            except Exception as e:
                # Skip players that can't be restored
                player_name = (
                    player_data.get("first_name", "") + " " + player_data.get("last_name", "")
                )
                print(f"Warning: Could not restore player {player_name.strip() or 'Unknown'}: {e}")
                continue

        await session.commit()

    def delete_save(self, save_name: str) -> bool:
        """Delete a save file."""
        save_path = self.save_dir / f"{save_name}{self.SAVE_EXTENSION}"

        if save_path.exists():
            save_path.unlink()
            return True
        return False

    def rename_save(self, old_name: str, new_name: str) -> str:
        """Rename a save file."""
        old_path = self.save_dir / f"{old_name}{self.SAVE_EXTENSION}"
        new_path = self.save_dir / f"{new_name}{self.SAVE_EXTENSION}"

        if not old_path.exists():
            raise FileNotFoundError(f"Save file not found: {old_name}")

        if new_path.exists():
            raise FileExistsError(f"Save file already exists: {new_name}")

        # Read, update metadata, and write with new name
        with gzip.open(old_path, "rt", encoding="utf-8") as f:
            save_data = json.load(f)

        save_data["metadata"]["save_name"] = new_name
        save_data["metadata"]["save_date"] = datetime.now().isoformat()

        with gzip.open(new_path, "wt", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, default=str)

        old_path.unlink()
        return str(new_path)

    def duplicate_save(self, source_name: str, new_name: str) -> str:
        """Duplicate a save file."""
        source_path = self.save_dir / f"{source_name}{self.SAVE_EXTENSION}"
        new_path = self.save_dir / f"{new_name}{self.SAVE_EXTENSION}"

        if not source_path.exists():
            raise FileNotFoundError(f"Save file not found: {source_name}")

        if new_path.exists():
            raise FileExistsError(f"Save file already exists: {new_name}")

        # Read and update metadata
        with gzip.open(source_path, "rt", encoding="utf-8") as f:
            save_data = json.load(f)

        save_data["metadata"]["save_name"] = new_name
        save_data["metadata"]["save_date"] = datetime.now().isoformat()

        with gzip.open(new_path, "wt", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, default=str)

        return str(new_path)

    def _capture_game_state(self, session: Session) -> GameState:
        """Capture complete game state from database."""
        state = GameState()

        # Export clubs
        clubs = session.execute(select(Club)).scalars().all()
        for club in clubs:
            state.clubs.append(self._object_to_dict(club))

        # Export players
        players = session.execute(select(Player)).scalars().all()
        for player in players:
            player_dict = self._object_to_dict(player)
            # Handle enum and date serialization
            if player.position:
                player_dict["position"] = player.position.value
            state.players.append(player_dict)

        # Export leagues
        leagues = session.execute(select(League)).scalars().all()
        for league in leagues:
            state.leagues.append(self._object_to_dict(league))

        # Export matches (last 200)
        matches = (
            session.execute(select(Match).order_by(Match.match_date.desc()).limit(200))
            .scalars()
            .all()
        )
        for match in matches:
            match_dict = self._object_to_dict(match)
            if match.match_date:
                match_dict["match_date"] = match.match_date.isoformat()
            state.matches.append(match_dict)

        # Export transfers (last 100)
        transfers = (
            session.execute(select(Transfer).order_by(Transfer.date.desc()).limit(100))
            .scalars()
            .all()
        )
        for transfer in transfers:
            transfer_dict = self._object_to_dict(transfer)
            if transfer.date:
                transfer_dict["date"] = transfer.date.isoformat()
            state.transfers.append(transfer_dict)

        # Export seasons
        seasons = session.execute(select(Season)).scalars().all()
        for season in seasons:
            season_dict = self._object_to_dict(season)
            if season.start_date:
                season_dict["start_date"] = season.start_date.isoformat()
            if season.end_date:
                season_dict["end_date"] = season.end_date.isoformat()
            state.seasons.append(season_dict)

        # Export cup competitions
        cup_comps = session.execute(select(CupCompetition)).scalars().all()
        for comp in cup_comps:
            state.cup_competitions.append(self._object_to_dict(comp))

        # Export cup editions
        cup_editions = session.execute(select(CupEdition)).scalars().all()
        for edition in cup_editions:
            edition_dict = self._object_to_dict(edition)
            if edition.start_date:
                edition_dict["start_date"] = edition.start_date.isoformat()
            if edition.end_date:
                edition_dict["end_date"] = edition.end_date.isoformat()
            state.cup_editions.append(edition_dict)

        # Export cup rounds
        cup_rounds = session.execute(select(CupRound)).scalars().all()
        for round_obj in cup_rounds:
            round_dict = self._object_to_dict(round_obj)
            if round_obj.scheduled_start:
                round_dict["scheduled_start"] = round_obj.scheduled_start.isoformat()
            if round_obj.scheduled_end:
                round_dict["scheduled_end"] = round_obj.scheduled_end.isoformat()
            state.cup_rounds.append(round_dict)

        # Export cup participants
        cup_participants = session.execute(select(CupParticipant)).scalars().all()
        for participant in cup_participants:
            state.cup_participants.append(self._object_to_dict(participant))

        # Export cup matches
        cup_matches = session.execute(select(CupMatch)).scalars().all()
        for cup_match in cup_matches:
            state.cup_matches.append(self._object_to_dict(cup_match))

        return state

    async def _capture_game_state_async(self, session: AsyncSession) -> GameState:
        """Capture complete game state from database (async version)."""
        state = GameState()

        # Export clubs - handle potential data issues gracefully
        try:
            result = await session.execute(select(Club))
            clubs = result.scalars().all()
            for club in clubs:
                try:
                    club_dict = self._object_to_dict(club)
                    state.clubs.append(club_dict)
                except Exception as e:
                    pass  # Skip clubs with data issues
        except Exception as e:
            print(f"Warning: Could not export clubs: {e}")

        # Export players
        result = await session.execute(select(Player))
        players = result.scalars().all()
        for player in players:
            player_dict = self._object_to_dict(player)
            if player.position:
                player_dict["position"] = player.position.value
            state.players.append(player_dict)

        # Export leagues
        result = await session.execute(select(League))
        leagues = result.scalars().all()
        for league in leagues:
            state.leagues.append(self._object_to_dict(league))

        # Export matches (last 200)
        result = await session.execute(select(Match).order_by(Match.match_date.desc()).limit(200))
        matches = result.scalars().all()
        for match in matches:
            match_dict = self._object_to_dict(match)
            if match.match_date:
                match_dict["match_date"] = match.match_date.isoformat()
            state.matches.append(match_dict)

        # Export transfers (last 100)
        result = await session.execute(
            select(Transfer).order_by(Transfer.offered_at.desc()).limit(100)
        )
        transfers = result.scalars().all()
        for transfer in transfers:
            transfer_dict = self._object_to_dict(transfer)
            if transfer.offered_at:
                transfer_dict["offered_at"] = transfer.offered_at.isoformat()
            state.transfers.append(transfer_dict)

        # Export seasons
        result = await session.execute(select(Season))
        seasons = result.scalars().all()
        for season in seasons:
            season_dict = self._object_to_dict(season)
            if season.start_date:
                season_dict["start_date"] = season.start_date.isoformat()
            if season.end_date:
                season_dict["end_date"] = season.end_date.isoformat()
            state.seasons.append(season_dict)

        # Export cup competitions
        result = await session.execute(select(CupCompetition))
        cup_comps = result.scalars().all()
        for comp in cup_comps:
            state.cup_competitions.append(self._object_to_dict(comp))

        # Export cup editions
        result = await session.execute(select(CupEdition))
        cup_editions = result.scalars().all()
        for edition in cup_editions:
            edition_dict = self._object_to_dict(edition)
            if edition.start_date:
                edition_dict["start_date"] = edition.start_date.isoformat()
            if edition.end_date:
                edition_dict["end_date"] = edition.end_date.isoformat()
            state.cup_editions.append(edition_dict)

        # Export cup rounds
        result = await session.execute(select(CupRound))
        cup_rounds = result.scalars().all()
        for round_obj in cup_rounds:
            round_dict = self._object_to_dict(round_obj)
            if round_obj.scheduled_start:
                round_dict["scheduled_start"] = round_obj.scheduled_start.isoformat()
            if round_obj.scheduled_end:
                round_dict["scheduled_end"] = round_obj.scheduled_end.isoformat()
            state.cup_rounds.append(round_dict)

        # Export cup participants
        result = await session.execute(select(CupParticipant))
        cup_participants = result.scalars().all()
        for participant in cup_participants:
            state.cup_participants.append(self._object_to_dict(participant))

        # Export cup matches
        result = await session.execute(select(CupMatch))
        cup_matches = result.scalars().all()
        for cup_match in cup_matches:
            state.cup_matches.append(self._object_to_dict(cup_match))

        return state

    def _object_to_dict(self, obj) -> Dict[str, Any]:
        """Convert SQLAlchemy object to dictionary."""
        from datetime import date, datetime

        result = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name)
            # Handle enum values - convert to string
            if hasattr(value, "value"):
                result[column.name] = value.value
            elif isinstance(value, Enum):
                result[column.name] = value.value
            elif isinstance(value, (date, datetime)):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

    def _calculate_statistics(
        self, session: Session, player_club_id: Optional[int]
    ) -> Dict[str, Any]:
        """Calculate game statistics for save metadata."""
        stats = {
            "matches_played": 0,
            "goals_scored": 0,
            "league_position": None,
        }

        if not player_club_id:
            return stats

        # Count matches played
        from sqlalchemy import func

        match_count = session.execute(
            select(func.count(Match.id)).where(
                (Match.home_club_id == player_club_id) | (Match.away_club_id == player_club_id)
            )
        ).scalar()
        stats["matches_played"] = match_count or 0

        # Count goals scored
        home_goals = (
            session.execute(
                select(func.sum(Match.home_score)).where(Match.home_club_id == player_club_id)
            ).scalar()
            or 0
        )

        away_goals = (
            session.execute(
                select(func.sum(Match.away_score)).where(Match.away_club_id == player_club_id)
            ).scalar()
            or 0
        )

        stats["goals_scored"] = home_goals + away_goals

        return stats

    async def _calculate_statistics_async(
        self, session: AsyncSession, player_club_id: Optional[int]
    ) -> Dict[str, Any]:
        """Calculate game statistics for save metadata (async version)."""
        stats = {
            "matches_played": 0,
            "goals_scored": 0,
            "league_position": None,
        }

        if not player_club_id:
            return stats

        from sqlalchemy import func

        result = await session.execute(
            select(func.count(Match.id)).where(
                (Match.home_club_id == player_club_id) | (Match.away_club_id == player_club_id)
            )
        )
        match_count = result.scalar()
        stats["matches_played"] = match_count or 0

        result = await session.execute(
            select(func.sum(Match.home_score)).where(Match.home_club_id == player_club_id)
        )
        home_goals = result.scalar() or 0

        result = await session.execute(
            select(func.sum(Match.away_score)).where(Match.away_club_id == player_club_id)
        )
        away_goals = result.scalar() or 0

        stats["goals_scored"] = home_goals + away_goals

        return stats

    def get_save_info(self, save_name: str) -> Dict[str, Any]:
        """Get detailed information about a save file."""
        save_path = self.save_dir / f"{save_name}{self.SAVE_EXTENSION}"

        if not save_path.exists():
            raise FileNotFoundError(f"Save file not found: {save_name}")

        # Get file stats
        file_stat = save_path.stat()
        file_size = file_stat.st_size

        # Read metadata
        metadata = self._read_save_metadata(save_path)

        return {
            "name": save_name,
            "path": str(save_path),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "created": datetime.fromtimestamp(file_stat.st_ctime),
            "modified": datetime.fromtimestamp(file_stat.st_mtime),
            "metadata": metadata.to_dict() if metadata else None,
        }


# Global save manager instance
_save_manager: Optional[EnhancedSaveLoadManager] = None


def get_save_manager(save_dir: Optional[Path] = None) -> EnhancedSaveLoadManager:
    """Get or create global save manager instance."""
    global _save_manager
    if _save_manager is None:
        _save_manager = EnhancedSaveLoadManager(save_dir)
    return _save_manager
