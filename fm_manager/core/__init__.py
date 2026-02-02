"""Core module for FM Manager."""

from fm_manager.core.config import settings, get_settings
from fm_manager.core.database import (
    Base,
    get_engine,
    get_session_maker,
    get_db_session,
    init_db,
    close_db,
)
from fm_manager.core.models import (
    Player,
    Club,
    League,
    Season,
    Match,
    Transfer,
    Position,
    ClubReputation,
    LeagueFormat,
    MatchStatus,
    TransferStatus,
)

__all__ = [
    # Config
    "settings",
    "get_settings",
    # Database
    "Base",
    "get_engine",
    "get_session_maker",
    "get_db_session",
    "init_db",
    "close_db",
    # Models
    "Player",
    "Club",
    "League",
    "Season",
    "Match",
    "Transfer",
    "Position",
    "ClubReputation",
    "LeagueFormat",
    "MatchStatus",
    "TransferStatus",
]
