"""Transfer engine for FM Manager.

Handles all transfer-related functionality:
- Transfer offers and negotiations
- Contract negotiations with players
- Transfer windows
- Player willingness logic
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum, auto
from typing import Callable, Union, Optional, Dict, List, Tuple

from fm_manager.core.models import Club, Player, TransferStatus


class TransferWindowType(Enum):
    """Types of transfer windows."""
    SUMMER = "summer"  # July-August
    WINTER = "winter"  # January


class OfferType(Enum):
    """Types of transfer offers."""
    TRANSFER = "transfer"  # Permanent transfer
    LOAN = "loan"          # Loan deal
    LOAN_WITH_OPTION = "loan_with_option"  # Loan with buy option
    LOAN_WITH_OBLIGATION = "loan_with_obligation"  # Loan with mandatory buy


class ContractType(Enum):
    """Contract types."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    YOUTH = "youth"


@dataclass
class TransferOffer:
    """A transfer offer from one club to another."""
    id: int = 0
    player_id: int = 0
    from_club_id: int = 0
    to_club_id: int = 0
    
    # Offer details
    offer_type: OfferType = OfferType.TRANSFER
    fee: int = 0  # Transfer fee
    
    # For loans
    loan_wage_split: int = 100  # % of wages paid by loaning club
    loan_duration_months: int = 0
    loan_fee: int = 0  # Monthly loan fee
    buy_option_fee: int = 0  # For loan with option
    buy_obligation_fee: int = 0  # For loan with obligation
    
    # Negotiation
    status: TransferStatus = TransferStatus.PENDING
    offered_at: date = field(default_factory=date.today)
    responded_at: Optional[date] = None
    
    # Counter offer
    counter_fee: Optional[int] = None
    counter_loan_fee: Optional[int] = None
    
    # Notes
    notes: str = ""
    
    def is_active(self) -> bool:
        """Check if offer is still active."""
        return self.status in {
            TransferStatus.PENDING,
            TransferStatus.NEGOTIATING,
            TransferStatus.ACCEPTED,
        }


@dataclass
class ContractOffer:
    """A contract offer to a player."""
    player_id: int = 0
    club_id: int = 0
    
    # Financial terms
    wage: int = 0  # Weekly wage
    contract_length_years: int = 3
    signing_on_fee: int = 0
    
    # Bonuses
    goal_bonus: int = 0
    clean_sheet_bonus: int = 0
    appearance_bonus: int = 0
    
    # Clauses
    release_clause: Optional[int] = None
    minimum_fee_clause: Optional[int] = None
    buy_back_clause: Optional[int] = None
    buy_back_club_id: Optional[int] = None
    
    # Squad role
    squad_role: str = "rotation"  # star, first_team, rotation, prospect
    promised_playing_time: int = 0  # Minutes per season expected
    
    # Status
    status: str = "pending"  # pending, accepted, rejected
    offered_at: date = field(default_factory=date.today)
    
    def calculate_total_cost(self) -> int:
        """Calculate total cost of contract over its length."""
        weeks = self.contract_length_years * 52
        total_wages = self.wage * weeks
        return total_wages + self.signing_on_fee


@dataclass
class PlayerTransferWillingness:
    """Player's willingness to transfer."""
    player_id: int = 0
    
    # Interest in move (0-100)
    interest_in_move: int = 50
    
    # Interest in specific clubs (club_id -> interest)
    club_interest: Dict[int, int] = field(default_factory=dict)
    
    # Reasons
    wants_more_playing_time: bool = False
    wants_better_wages: bool = False
    wants_champions_league: bool = False
    wants_to_return_home: bool = False
    
    # Loyalty (reduces willingness to leave)
    loyalty_to_current_club: int = 50
    years_at_club: int = 0
    
    def calculate_willingness_for_club(self, club_id: int, club_reputation: int) -> int:
        """Calculate willingness to join a specific club."""
        base = self.interest_in_move
        
        # Club-specific interest
        club_interest = self.club_interest.get(club_id, 50)
        
        # Loyalty penalty
        loyalty_penalty = self.loyalty_to_current_club // 4  # 0-25 penalty
        
        # Blend factors
        willingness = (base * 0.4) + (club_interest * 0.4) - loyalty_penalty
        
        # Adjust for reputation (players more willing to join big clubs)
        if club_reputation > 8000:
            willingness += 10
        elif club_reputation > 6000:
            willingness += 5
        
        return max(0, min(100, int(willingness)))


@dataclass
class TransferWindow:
    """Represents a transfer window period."""
    window_type: TransferWindowType
    start_date: date
    end_date: date
    is_open: bool = False
    
    def is_date_in_window(self, check_date: date) -> bool:
        """Check if a date falls within this window."""
        return self.start_date <= check_date <= self.end_date
    
    def days_remaining(self, current_date: date) -> int:
        """Get days remaining in window."""
        if not self.is_open:
            return 0
        days = (self.end_date - current_date).days
        return max(0, days)


class TransferWindowManager:
    """Manages transfer windows for leagues."""
    
    # Standard European windows
    SUMMER_START = (7, 1)   # July 1
    SUMMER_END = (8, 31)    # August 31
    WINTER_START = (1, 1)   # January 1
    WINTER_END = (1, 31)    # January 31
    
    def __init__(self, year: int = 2024):
        self.year = year
        self.windows: list[TransferWindow] = []
        self._setup_windows()
    
    def _setup_windows(self) -> None:
        """Setup standard transfer windows."""
        # Summer window
        summer_start = date(self.year, *self.SUMMER_START)
        summer_end = date(self.year, *self.SUMMER_END)
        
        self.windows.append(TransferWindow(
            window_type=TransferWindowType.SUMMER,
            start_date=summer_start,
            end_date=summer_end,
        ))
        
        # Winter window
        winter_start = date(self.year + 1, *self.WINTER_START)
        winter_end = date(self.year + 1, *self.WINTER_END)
        
        self.windows.append(TransferWindow(
            window_type=TransferWindowType.WINTER,
            start_date=winter_start,
            end_date=winter_end,
        ))
    
    def is_window_open(self, check_date: Optional[date] = None) -> bool:
        """Check if any transfer window is open."""
        if check_date is None:
            check_date = date.today()
        
        for window in self.windows:
            if window.is_date_in_window(check_date):
                return True
        return False
    
    def get_active_window(self, check_date: Optional[date] = None) -> Optional[TransferWindow]:
        """Get the currently active transfer window."""
        if check_date is None:
            check_date = date.today()
        
        for window in self.windows:
            if window.is_date_in_window(check_date):
                return window
        return None
    
    def days_until_next_window(self, current_date: date) -> int:
        """Get days until next transfer window opens."""
        for window in self.windows:
            if window.start_date > current_date:
                return (window.start_date - current_date).days
        
        # If past all windows, calculate for next year's summer
        next_summer = date(current_date.year + 1, *self.SUMMER_START)
        return (next_summer - current_date).days


class PlayerValuationCalculator:
    """Calculate player market values."""
    
    def __init__(self):
        pass
    
    def calculate_value(
        self,
        player: Player,
        age_factor: bool = True,
        contract_factor: bool = True,
        form_factor: bool = True,
    ) -> int:
        """Calculate a player's market value.
        
        Factors:
        - Current ability
        - Potential ability (for young players)
        - Age (peak at 25-28)
        - Contract length
        - Current form
        """
        base_value = player.current_ability * 100_000  # €100k per ability point
        
        # Age factor
        if age_factor:
            age = player.age or 25
            if age < 21:
                age_multiplier = 0.7 + (age - 16) * 0.06  # 0.7 to 1.0
            elif age <= 25:
                age_multiplier = 1.0 + (age - 21) * 0.05  # 1.0 to 1.2
            elif age <= 28:
                age_multiplier = 1.2  # Peak years
            elif age <= 32:
                age_multiplier = 1.2 - (age - 28) * 0.1  # 1.2 to 0.8
            else:
                age_multiplier = 0.8 - (age - 32) * 0.05  # Declining
            
            age_multiplier = max(0.3, min(1.3, age_multiplier))
            base_value *= age_multiplier
        
        # Potential factor (for young players)
        potential_gap = (player.potential_ability or player.current_ability) - player.current_ability
        if potential_gap > 10 and age_factor:
            potential_bonus = potential_gap * 50_000  # €50k per potential point
            base_value += potential_bonus
        
        # Contract factor
        if contract_factor:
            contract_years = self._estimate_contract_years(player)
            if contract_years < 1:
                base_value *= 0.5  # Expiring contract - low value
            elif contract_years < 2:
                base_value *= 0.7
            elif contract_years > 3:
                base_value *= 1.1  # Long contract - premium
        
        # Form factor
        if form_factor and player.form:
            form_multiplier = 0.8 + (player.form / 100) * 0.4  # 0.8 to 1.2
            base_value *= form_multiplier
        
        return int(base_value)
    
    def _estimate_contract_years(self, player: Player) -> float:
        """Estimate remaining contract years."""
        if not player.contract_until:
            return 2.0  # Assume 2 years if unknown
        
        days_remaining = (player.contract_until - date.today()).days
        return max(0, days_remaining / 365)
    
    def suggest_asking_price(
        self,
        player: Player,
        selling_club_reputation: int = 5000,
        buying_club_reputation: int = 5000,
    ) -> int:
        """Suggest an asking price for a player."""
        base_value = self.calculate_value(player)
        
        # Rich clubs pay more
        if buying_club_reputation > selling_club_reputation + 2000:
            premium = 0.2  # 20% premium for rich clubs
        else:
            premium = 0.0
        
        # Star player premium
        if player.current_ability > 85:
            star_premium = 0.3
        elif player.current_ability > 80:
            star_premium = 0.15
        else:
            star_premium = 0.0
        
        return int(base_value * (1 + premium + star_premium))


class ContractNegotiator:
    """Handle contract negotiations with players."""
    
    def __init__(self):
        self.rng = random.Random()
    
    def calculate_player_wage_demand(
        self,
        player: Player,
        club_reputation: int,
        is_champions_league: bool = False,
    ) -> int:
        """Calculate what wage a player will demand.
        
        Factors:
        - Current ability
        - Age
        - Current wage
        - Club reputation
        - Champions League status
        """
        base_wage = player.salary or 5000
        
        # Ability factor
        ability_multiplier = 1.0 + (player.current_ability - 50) / 100  # 0.5 to 1.5
        
        # Age factor (older players demand more security)
        age = player.age or 25
        if age > 30:
            age_multiplier = 1.1  # Want final big contract
        else:
            age_multiplier = 1.0
        
        # Club reputation factor
        rep_multiplier = 0.8 + (club_reputation / 10000) * 0.4  # 0.8 to 1.2
        
        # Champions League bonus
        cl_multiplier = 1.15 if is_champions_league else 1.0
        
        demanded_wage = int(base_wage * ability_multiplier * age_multiplier * rep_multiplier * cl_multiplier)
        
        # Add some randomness
        variation = self.rng.gauss(0, demanded_wage * 0.1)
        
        return max(1000, int(demanded_wage + variation))
    
    def evaluate_contract_offer(
        self,
        player: Player,
        offer: ContractOffer,
        current_club_offer: Optional[ContractOffer] = None,
    ) -> dict:
        """Evaluate a contract offer from a player's perspective.
        
        Returns:
            dict with acceptance probability and reasons
        """
        reasons = []
        score = 50  # Base score
        
        # Wage comparison
        current_wage = player.salary or 5000
        wage_increase = (offer.wage - current_wage) / current_wage * 100
        
        if wage_increase > 50:
            score += 30
            reasons.append(f"Excellent wage increase (+{wage_increase:.0f}%)")
        elif wage_increase > 20:
            score += 15
            reasons.append(f"Good wage increase (+{wage_increase:.0f}%)")
        elif wage_increase > 0:
            score += 5
            reasons.append(f"Modest wage increase (+{wage_increase:.0f}%)")
        elif wage_increase < -10:
            score -= 20
            reasons.append(f"Wage decrease ({wage_increase:.0f}%)")
        
        # Squad role
        role_scores = {
            "star": 20,
            "first_team": 10,
            "rotation": 0,
            "prospect": -10,
        }
        score += role_scores.get(offer.squad_role, 0)
        
        # Contract length
        if offer.contract_length_years >= 4:
            score += 10
            reasons.append("Long-term security")
        elif offer.contract_length_years == 1:
            score -= 10
            reasons.append("Short contract")
        
        # Signing on fee
        if offer.signing_on_fee > offer.wage * 10:  # More than 10 weeks wages
            score += 10
            reasons.append("Attractive signing bonus")
        
        # Random factor (player's mood, agent advice, etc.)
        random_factor = self.rng.randint(-10, 10)
        score += random_factor
        
        # Cap score
        score = max(0, min(100, score))
        
        # Determine acceptance
        acceptance_threshold = self.rng.randint(60, 80)
        will_accept = score >= acceptance_threshold
        
        return {
            "score": score,
            "threshold": acceptance_threshold,
            "will_accept": will_accept,
            "reasons": reasons,
            "probability": score / 100,
        }


class TransferEngine:
    """Main transfer engine."""
    
    def __init__(self):
        self.valuation_calculator = PlayerValuationCalculator()
        self.contract_negotiator = ContractNegotiator()
        self.window_manager: Optional[TransferWindowManager] = None
    
    def initialize_for_season(self, year: int) -> None:
        """Initialize transfer windows for a season."""
        self.window_manager = TransferWindowManager(year)
    
    def can_make_offer(
        self,
        buying_club: Club,
        selling_club: Club,
        player: Player,
        current_date: date,
    ) -> Tuple[bool, str]:
        """Check if a transfer offer can be made.
        
        Returns:
            (can_offer, reason)
        """
        # Check transfer window
        if self.window_manager and not self.window_manager.is_window_open(current_date):
            return False, "Transfer window is closed"
        
        # Check if player is already transferring
        if player.club_id != selling_club.id:
            return False, "Player is no longer at this club"
        
        # Check buying club finances
        if buying_club.balance < 0:
            return False, "Buying club has insufficient funds"
        
        return True, "Offer can be made"
    
    def create_transfer_offer(
        self,
        player: Player,
        from_club: Club,
        to_club: Club,
        fee: int,
        offer_type: OfferType = OfferType.TRANSFER,
    ) -> TransferOffer:
        """Create a new transfer offer."""
        offer = TransferOffer(
            player_id=player.id,
            from_club_id=from_club.id,
            to_club_id=to_club.id,
            offer_type=offer_type,
            fee=fee,
            status=TransferStatus.PENDING,
        )
        return offer
    
    def evaluate_transfer_offer(
        self,
        offer: TransferOffer,
        player: Player,
        selling_club: Club,
        buying_club: Club,
    ) -> dict:
        """Evaluate a transfer offer from selling club's perspective.
        
        Returns:
            dict with decision and reasoning
        """
        # Get player valuation
        player_value = self.valuation_calculator.calculate_value(player)
        
        # Calculate acceptance score
        score = 50  # Base
        
        # Fee vs value
        fee_ratio = offer.fee / player_value if player_value > 0 else 0
        
        if fee_ratio >= 1.5:
            score += 40
        elif fee_ratio >= 1.2:
            score += 25
        elif fee_ratio >= 1.0:
            score += 10
        elif fee_ratio >= 0.8:
            score -= 10
        else:
            score -= 30
        
        # Player importance
        if player.current_ability > 80:
            score -= 20  # Reluctant to sell stars
        
        # Club needs
        if selling_club.balance < 0:
            score += 20  # Need the money
        
        # Random factor
        random_factor = random.randint(-10, 10)
        score += random_factor
        
        score = max(0, min(100, score))
        
        # Decision
        if score >= 70:
            decision = "accept"
        elif score >= 40:
            decision = "counter"
        else:
            decision = "reject"
        
        return {
            "score": score,
            "decision": decision,
            "player_value": player_value,
            "fee_ratio": fee_ratio,
        }
