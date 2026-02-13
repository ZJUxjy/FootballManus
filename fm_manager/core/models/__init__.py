"""Core models for FM Manager."""

from fm_manager.core.models.player import Player, Position, WorkRate, Foot
from fm_manager.core.models.club import Club, ClubReputation
from fm_manager.core.models.league import League, LeagueFormat, Season
from fm_manager.core.models.match import Match, MatchStatus, MatchEventType
from fm_manager.core.models.transfer import Transfer, TransferStatus, TransferWindow
from fm_manager.core.models.cup_competition import (
    CupCompetition,
    CupEdition,
    CupRound,
    CupParticipant,
    CupMatch,
    CupPrizeMoney,
    CupType,
    CupFormat,
    CupRoundType,
    CupStatus,
)
from fm_manager.core.models.facility import (
    Facility,
    FacilityType,
    FacilityLevelConfig,
)
from fm_manager.core.models.staff import Staff, StaffRole, StaffEffect

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
    "CupCompetition",
    "CupEdition",
    "CupRound",
    "CupParticipant",
    "CupMatch",
    "CupPrizeMoney",
    "CupType",
    "CupFormat",
    "CupRoundType",
    "CupStatus",
    # Facility
    "Facility",
    "FacilityType",
    "FacilityLevelConfig",
    # Staff
    "Staff",
    "StaffRole",
    "StaffEffect",
]
