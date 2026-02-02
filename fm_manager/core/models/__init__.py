"""Core models for FM Manager."""

from fm_manager.core.models.player import Player, Position, WorkRate, Foot
from fm_manager.core.models.club import Club, ClubReputation
from fm_manager.core.models.league import League, LeagueFormat, Season
from fm_manager.core.models.match import Match, MatchStatus, MatchEventType
from fm_manager.core.models.transfer import Transfer, TransferStatus, TransferWindow

__all__ = [
    # Player
    "Player",
    "Position",
    "WorkRate",
    "Foot",
    # Club
    "Club",
    "ClubReputation",
    # League
    "League",
    "LeagueFormat",
    "Season",
    # Match
    "Match",
    "MatchStatus",
    "MatchEventType",
    # Transfer
    "Transfer",
    "TransferStatus",
    "TransferWindow",
]
