"""Sponsorship manager for FM Manager."""

from datetime import date, timedelta
from random import choice, gauss, randint, uniform
from typing import List, Optional, Tuple, Dict, Any

from fm_manager.core.models.sponsorship import (
    Sponsor,
    SponsorLevel,
    SponsorType,
    SponsorshipDeal,
    ContractStatus,
    SPONSOR_PAYMENT_RANGES,
    SPONSOR_LEVEL_REPUTATION_REQUIREMENTS,
    SPONSOR_TYPE_MULTIPLIERS,
)
from fm_manager.core.models.club import Club


class SponsorshipManager:
    """Manages all sponsorship-related operations."""
    
    def __init__(self):
        self.sponsor_database: List[Sponsor] = []
        self.active_deals: List[SponsorshipDeal] = []
    
    def get_all_sponsors(self, club_id: Optional[int] = None) -> List[Sponsor]:
        """Get all sponsors, optionally filtered by club.
        
        Args:
            club_id: If provided, only return sponsors for this club
            
        Returns:
            List of Sponsor objects
        """
        if club_id is not None:
            return [s for s in self.sponsor_database if s.club_id == club_id]
        return self.sponsor_database
    
    def find_potential_sponsors(
        self,
        club: Club,
        sponsor_type: Optional[SponsorType] = None,
        min_level: SponsorLevel = SponsorLevel.LOCAL,
    ) -> List[Sponsor]:
        """Find potential sponsors for a club based on reputation.
        
        Args:
            club: The club seeking sponsors
            sponsor_type: Optional filter by sponsor type
            min_level: Minimum sponsor level to consider
            
        Returns:
            List of potential Sponsor objects
        """
        potential = []
        
        for sponsor in self.sponsor_database:
            # Skip sponsors already attached to a club
            if sponsor.club_id is not None and sponsor.club_id != club.id:
                continue
            
            # Skip if sponsor level is below minimum
            if sponsor.level.value < min_level.value:
                continue
            
            # Check if club meets sponsor's minimum reputation requirement
            if club.reputation < sponsor.min_club_reputation:
                continue
            
            # Check if club meets level requirement
            min_rep_for_level = SPONSOR_LEVEL_REPUTATION_REQUIREMENTS.get(sponsor.level, 0)
            if club.reputation < min_rep_for_level:
                continue
            
            # Filter by type if specified
            if sponsor_type is not None and sponsor.sponsor_type != sponsor_type:
                continue
            
            potential.append(sponsor)
        
        # Sort by relevance (sponsors who specifically want this club's level come first)
        potential.sort(key=lambda s: abs(s.min_club_reputation - club.reputation))
        
        return potential
    
    def calculate_max_sponsor_level(self, club_reputation: int) -> SponsorLevel:
        """Calculate the maximum sponsor level a club can attract.
        
        Args:
            club_reputation: Club's reputation score (0-10000)
            
        Returns:
            Maximum achievable SponsorLevel
        """
        for level, min_rep in sorted(
            SPONSOR_LEVEL_REPUTATION_REQUIREMENTS.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if club_reputation >= min_rep:
                return level
        return SponsorLevel.LOCAL
    
    def calculate_sponsor_payment_range(
        self,
        club_reputation: int,
        sponsor_level: SponsorLevel,
        sponsor_type: SponsorType,
    ) -> Tuple[int, int]:
        """Calculate payment range for a sponsor deal.
        
        Args:
            club_reputation: Club's reputation
            sponsor_level: Level of sponsor
            sponsor_type: Type of sponsorship
            
        Returns:
            Tuple of (min_payment, max_payment) in EUR
        """
        base_min, base_max = SPONSOR_PAYMENT_RANGES[sponsor_level]
        
        # Adjust based on club reputation within level
        max_rep_for_level = self._get_max_reputation_for_level(sponsor_level)
        min_rep_for_level = SPONSOR_LEVEL_REPUTATION_REQUIREMENTS[sponsor_level]
        
        if max_rep_for_level > min_rep_for_level:
            reputation_factor = (club_reputation - min_rep_for_level) / (
                max_rep_for_level - min_rep_for_level
            )
        else:
            reputation_factor = 1.0
        
        # Apply type multiplier
        type_multiplier = SPONSOR_TYPE_MULTIPLIERS.get(sponsor_type, 0.1)
        
        adjusted_min = int(base_min * (0.8 + 0.2 * reputation_factor) * type_multiplier)
        adjusted_max = int(base_max * (0.9 + 0.1 * reputation_factor) * type_multiplier)
        
        return adjusted_min, adjusted_max
    
    def _get_max_reputation_for_level(self, level: SponsorLevel) -> int:
        """Get the maximum reputation that qualifies for a sponsor level."""
        levels = sorted(SponsorLevel, key=lambda l: l.value, reverse=True)
        level_idx = levels.index(level)
        
        if level_idx == 0:
            return 10000
        
        next_level = levels[level_idx - 1]
        return SPONSOR_LEVEL_REPUTATION_REQUIREMENTS[next_level] - 1
    
    def negotiate_sponsor(
        self,
        sponsor: Sponsor,
        club: Club,
        proposed_annual_payment: int,
        contract_years: int = 3,
        performance_bonus_rate: float = 0.0,
    ) -> Tuple[bool, SponsorshipDeal, str]:
        """Negotiate a sponsorship deal.
        
        Args:
            sponsor: The sponsor to negotiate with
            club: The club seeking sponsorship
            proposed_annual_payment: Club's offer
            contract_years: Length of contract
            performance_bonus_rate: Proposed bonus rate
            
        Returns:
            Tuple of (success, deal, message)
        """
        # Calculate acceptable range
        min_payment, max_payment = self.calculate_sponsor_payment_range(
            club.reputation, sponsor.level, sponsor.sponsor_type
        )
        
        # Sponsor's minimum acceptable is typically 80% of their target
        sponsor_min = int(min_payment * 0.8)
        
        # Create deal object
        deal = SponsorshipDeal(
            sponsor_id=sponsor.id,
            sponsor_name=sponsor.name,
            sponsor_level=sponsor.level,
            sponsor_type=sponsor.sponsor_type,
            club_id=club.id,
            club_name=club.name,
            annual_payment=proposed_annual_payment,
            contract_length_years=contract_years,
            performance_bonus_rate=performance_bonus_rate,
            initial_offer=proposed_annual_payment,
            current_offer=proposed_annual_payment,
            sponsor_min_acceptable=sponsor_min,
            proposed_start=date.today(),
            proposed_end=date.today() + timedelta(days=365 * contract_years),
            status=ContractStatus.NEGOTIATING,
        )
        
        # Check if offer is acceptable
        if proposed_annual_payment >= sponsor_min:
            # Success - offer is good enough
            deal.status = ContractStatus.ACTIVE
            
            # Update sponsor record
            sponsor.club_id = club.id
            sponsor.base_annual_payment = proposed_annual_payment
            sponsor.performance_bonus_rate = performance_bonus_rate
            sponsor.contract_start = deal.proposed_start
            sponsor.contract_end = deal.proposed_end
            sponsor.status = ContractStatus.ACTIVE
            sponsor.negotiation_count += 1
            sponsor.last_negotiation_date = date.today()
            
            self.active_deals.append(deal)
            
            return True, deal, f"Deal accepted! {sponsor.name} will pay €{proposed_annual_payment:,}/year."
        else:
            # Failure - offer too low
            deal.negotiation_round += 1
            
            # Calculate counter offer
            counter = int((sponsor_min + proposed_annual_payment) / 2)
            deal.current_offer = counter
            
            message = (
                f"Offer rejected. {sponsor.name} wants at least €{sponsor_min:,}/year. "
                f"Counter offer: €{counter:,}/year."
            )
            
            return False, deal, message
    
    def renew_contract(
        self,
        sponsor: Sponsor,
        new_annual_payment: Optional[int] = None,
        extension_years: int = 3,
    ) -> Tuple[bool, str]:
        """Renew an existing sponsorship contract.
        
        Args:
            sponsor: The sponsor to renew with
            new_annual_payment: New payment amount (if None, increase by 10%)
            extension_years: Years to extend
            
        Returns:
            Tuple of (success, message)
        """
        if not sponsor.can_renew:
            return False, "Contract cannot be renewed at this time."
        
        if new_annual_payment is None:
            # Default to 10% increase
            new_annual_payment = int(sponsor.base_annual_payment * 1.1)
        
        # Calculate new range based on current club reputation
        club = sponsor.club
        if club is None:
            return False, "Sponsor has no associated club."
        
        min_payment, max_payment = self.calculate_sponsor_payment_range(
            club.reputation, sponsor.level, sponsor.sponsor_type
        )
        
        # Check if new payment is acceptable
        if new_annual_payment < min_payment * 0.9:
            return (
                False,
                f"Offer too low. Minimum acceptable: €{int(min_payment * 0.9):,}/year"
            )
        
        # Update contract
        old_end = sponsor.contract_end
        sponsor.base_annual_payment = new_annual_payment
        sponsor.contract_start = date.today()
        
        if old_end and old_end > date.today():
            # Contract still active - extend from current end
            sponsor.contract_end = old_end + timedelta(days=365 * extension_years)
        else:
            # Contract expired - start new
            sponsor.contract_end = date.today() + timedelta(days=365 * extension_years)
        
        sponsor.status = ContractStatus.ACTIVE
        sponsor.negotiation_count += 1
        sponsor.last_negotiation_date = date.today()
        
        return (
            True,
            f"Contract renewed! New terms: €{new_annual_payment:,}/year until {sponsor.contract_end}."
        )
    
    def terminate_contract(
        self,
        sponsor: Sponsor,
        termination_fee: Optional[int] = None,
    ) -> Tuple[bool, int, str]:
        """Terminate a sponsorship contract.
        
        Args:
            sponsor: The sponsor contract to terminate
            termination_fee: Fee to pay (if None, calculated automatically)
            
        Returns:
            Tuple of (success, fee_paid, message)
        """
        if sponsor.status != ContractStatus.ACTIVE:
            return False, 0, "Contract is not active."
        
        # Calculate termination fee (typically 50% of remaining contract value)
        if termination_fee is None:
            if sponsor.contract_end:
                remaining_weeks = sponsor.contract_remaining_days // 7
                remaining_value = sponsor.weekly_payment * remaining_weeks
                termination_fee = int(remaining_value * 0.5)
            else:
                termination_fee = int(sponsor.base_annual_payment * 0.5)
        
        # Update sponsor status
        sponsor.status = ContractStatus.TERMINATED
        sponsor.club_id = None
        sponsor.base_annual_payment = 0
        sponsor.contract_end = date.today()
        
        # Remove from active deals
        self.active_deals = [
            d for d in self.active_deals
            if not (d.sponsor_id == sponsor.id and d.club_id == sponsor.club_id)
        ]
        
        return (
            True,
            termination_fee,
            f"Contract terminated. Termination fee: €{termination_fee:,}."
        )
    
    def calculate_weekly_income(self, club_id: int) -> int:
        """Calculate total weekly sponsorship income for a club.
        
        Args:
            club_id: The club ID
            
        Returns:
            Total weekly income in EUR
        """
        total = 0
        for sponsor in self.sponsor_database:
            if sponsor.club_id == club_id and sponsor.is_active:
                total += sponsor.weekly_payment
        return total
    
    def calculate_performance_bonuses(
        self,
        club_id: int,
        period_matches: int = 0,
        period_wins: int = 0,
        period_goals: int = 0,
    ) -> Dict[int, int]:
        """Calculate performance bonuses for all active sponsors.
        
        Args:
            club_id: The club ID
            period_matches: Matches played in period
            period_wins: Wins in period
            period_goals: Goals scored in period
            
        Returns:
            Dictionary of sponsor_id -> bonus_amount
        """
        bonuses = {}
        
        for sponsor in self.sponsor_database:
            if sponsor.club_id == club_id and sponsor.is_active:
                bonus = sponsor.calculate_performance_bonus(
                    period_matches, period_wins, period_goals
                )
                if bonus > 0:
                    bonuses[sponsor.id] = bonus
        
        return bonuses
    
    def generate_random_sponsor(
        self,
        level: SponsorLevel,
        sponsor_type: SponsorType,
        industry: Optional[str] = None,
    ) -> Sponsor:
        """Generate a random sponsor for testing/initialization.
        
        Args:
            level: Sponsor level
            sponsor_type: Type of sponsorship
            industry: Industry sector (if None, randomly selected)
            
        Returns:
            New Sponsor object
        """
        industries = [
            "Technology", "Finance", "Automotive", "Airlines", "Energy",
            "Gambling", "Telecommunications", "Consumer Goods", "Sports Equipment",
            "Cryptocurrency", "E-commerce", "Insurance", "Banking", "Retail"
        ]
        
        if industry is None:
            industry = choice(industries)
        
        # Generate payment amount
        min_payment, max_payment = SPONSOR_PAYMENT_RANGES[level]
        base_payment = randint(min_payment, max_payment)
        
        # Generate sponsor name
        name_prefixes = ["Global", "Premier", "Elite", "United", "World", "Prime", "Royal"]
        name_suffixes = ["Corp", "Group", "Holdings", "International", "Enterprises", "Solutions"]
        
        if level == SponsorLevel.GLOBAL:
            name = f"{choice(name_prefixes)} {industry} {choice(name_suffixes)}"
        elif level == SponsorLevel.PREMIUM:
            name = f"{industry} {choice(name_suffixes)}"
        elif level == SponsorLevel.MAJOR:
            name = f"{industry} Partners"
        else:
            name = f"{industry} Ltd"
        
        # Create sponsor
        sponsor = Sponsor(
            name=name,
            industry=industry,
            level=level,
            sponsor_type=sponsor_type,
            base_annual_payment=0,  # Will be set during negotiation
            performance_bonus_rate=uniform(0.05, 0.15),
            max_annual_bonus=int(base_payment * 0.2),
            reputation=randint(50, 100) if level.value >= 3 else randint(20, 60),
            min_club_reputation=SPONSOR_LEVEL_REPUTATION_REQUIREMENTS[level],
            status=ContractStatus.PENDING,
        )
        
        return sponsor
    
    def get_club_sponsorship_summary(self, club_id: int) -> Dict[str, Any]:
        """Get a summary of all sponsorships for a club.
        
        Args:
            club_id: The club ID
            
        Returns:
            Dictionary with sponsorship summary
        """
        club_sponsors = [s for s in self.sponsor_database if s.club_id == club_id]
        active_sponsors = [s for s in club_sponsors if s.is_active]
        
        total_annual = sum(s.base_annual_payment for s in active_sponsors)
        total_weekly = sum(s.weekly_payment for s in active_sponsors)
        
        by_type: Dict[str, List[Dict]] = {}
        for sponsor in active_sponsors:
            type_key = sponsor.sponsor_type.value
            if type_key not in by_type:
                by_type[type_key] = []
            by_type[type_key].append(sponsor.to_dict())
        
        expiring_soon = [
            s.to_dict() for s in active_sponsors
            if s.contract_remaining_days <= 90
        ]
        
        return {
            "club_id": club_id,
            "total_sponsors": len(club_sponsors),
            "active_sponsors": len(active_sponsors),
            "total_annual_income": total_annual,
            "total_weekly_income": total_weekly,
            "sponsors_by_type": by_type,
            "expiring_soon": expiring_soon,
        }
    
    def process_weekly_sponsorship_payments(self, club_id: int) -> int:
        """Process weekly sponsorship payments for a club.
        
        Args:
            club_id: The club ID
            
        Returns:
            Total amount paid this week
        """
        total_paid = 0
        
        for sponsor in self.sponsor_database:
            if sponsor.club_id == club_id and sponsor.is_active:
                total_paid += sponsor.weekly_payment
                
                # Update performance tracking
                sponsor.matches_sponsored += 1
        
        return total_paid
