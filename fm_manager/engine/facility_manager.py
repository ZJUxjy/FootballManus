"""Facility manager for handling club facility operations.

Manages facility upgrades, maintenance costs, and effect calculations.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from fm_manager.core.models.facility import (
    Facility,
    FacilityType,
    FacilityLevelConfig,
    get_facility_config,
    get_level_config,
    calculate_upgrade_cost,
    calculate_maintenance_cost,
)
from fm_manager.core.models.club import Club


class FacilityManager:
    """Manager class for club facility operations.
    
    Handles facility queries, upgrades, and effect calculations.
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
    
    async def get_facility(
        self, 
        club_id: int, 
        facility_type: FacilityType
    ) -> Optional[Facility]:
        """Get a specific facility for a club.
        
        Args:
            club_id: ID of the club
            facility_type: Type of facility to retrieve
            
        Returns:
            Facility if found, None otherwise
        """
        result = await self.session.execute(
            select(Facility).where(
                and_(
                    Facility.club_id == club_id,
                    Facility.facility_type == facility_type
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all_facilities(self, club_id: int) -> list[Facility]:
        """Get all facilities for a club.
        
        Args:
            club_id: ID of the club
            
        Returns:
            List of all facilities for the club
        """
        result = await self.session.execute(
            select(Facility).where(Facility.club_id == club_id)
        )
        return list(result.scalars().all())
    
    async def get_facility_level(
        self, 
        club_id: int, 
        facility_type: FacilityType
    ) -> int:
        """Get the current level of a specific facility.
        
        Args:
            club_id: ID of the club
            facility_type: Type of facility
            
        Returns:
            Current facility level (1-20), or 1 if not found
        """
        facility = await self.get_facility(club_id, facility_type)
        return facility.level if facility else 1
    
    async def can_upgrade(
        self, 
        club_id: int, 
        facility_type: FacilityType
    ) -> tuple[bool, str]:
        """Check if a facility can be upgraded.
        
        Args:
            club_id: ID of the club
            facility_type: Type of facility to upgrade
            
        Returns:
            Tuple of (can_upgrade, reason)
            - can_upgrade: True if upgrade is possible
            - reason: Message explaining why or why not
        """
        facility = await self.get_facility(club_id, facility_type)
        
        if facility is None:
            return False, f"Facility {facility_type.value} does not exist for this club"
        
        if facility.is_max_level:
            return False, f"{facility_type.value} is already at maximum level (20)"
        
        club = await self.session.get(Club, club_id)
        if club is None:
            return False, "Club not found"
        
        upgrade_cost = facility.upgrade_cost
        if club.balance < upgrade_cost:
            return False, f"Insufficient funds. Need {upgrade_cost:,}, have {club.balance:,}"
        
        return True, f"Upgrade available for {upgrade_cost:,}"
    
    async def upgrade_facility(
        self, 
        club_id: int, 
        facility_type: FacilityType
    ) -> tuple[bool, str, Optional[Facility]]:
        """Upgrade a facility to the next level.
        
        Args:
            club_id: ID of the club
            facility_type: Type of facility to upgrade
            
        Returns:
            Tuple of (success, message, updated_facility)
        """
        can_upgrade, reason = await self.can_upgrade(club_id, facility_type)
        
        if not can_upgrade:
            return False, reason, None
        
        facility = await self.get_facility(club_id, facility_type)
        club = await self.session.get(Club, club_id)
        
        upgrade_cost = facility.upgrade_cost
        
        # Deduct cost
        club.balance -= upgrade_cost
        
        # Upgrade level
        old_level = facility.level
        facility.level += 1
        
        # Recalculate costs for new level
        config = get_facility_config(facility_type)
        facility.upgrade_cost = calculate_upgrade_cost(facility_type, facility.level)
        facility.weekly_maintenance = calculate_maintenance_cost(facility_type, facility.level)
        
        await self.session.commit()
        
        return True, (
            f"{facility_type.value.replace('_', ' ').title()} upgraded "
            f"from level {old_level} to {facility.level}"
        ), facility
    
    async def calculate_weekly_maintenance(self, club_id: int) -> int:
        """Calculate total weekly maintenance cost for all club facilities.
        
        Args:
            club_id: ID of the club
            
        Returns:
            Total weekly maintenance cost in currency units
        """
        facilities = await self.get_all_facilities(club_id)
        return sum(facility.weekly_maintenance for facility in facilities)
    
    async def calculate_monthly_maintenance(self, club_id: int) -> int:
        """Calculate total monthly maintenance cost for all club facilities.
        
        Args:
            club_id: ID of the club
            
        Returns:
            Total monthly maintenance cost (weekly * 4)
        """
        weekly = await self.calculate_weekly_maintenance(club_id)
        return weekly * 4
    
    async def calculate_yearly_maintenance(self, club_id: int) -> int:
        """Calculate total yearly maintenance cost for all club facilities.
        
        Args:
            club_id: ID of the club
            
        Returns:
            Total yearly maintenance cost (weekly * 52)
        """
        weekly = await self.calculate_weekly_maintenance(club_id)
        return weekly * 52
    
    def get_youth_academy_bonus(self, facility: Optional[Facility]) -> float:
        """Calculate youth academy quality bonus.
        
        Args:
            facility: Youth academy facility
            
        Returns:
            Bonus multiplier (e.g., 1.35 for +35% quality)
        """
        if facility is None or facility.facility_type != FacilityType.YOUTH_ACADEMY:
            return 1.0
        return 1.0 + facility.effect_percentage
    
    def get_training_efficiency_bonus(self, facility: Optional[Facility]) -> float:
        """Calculate training ground efficiency bonus.
        
        Args:
            facility: Training ground facility
            
        Returns:
            Bonus multiplier (e.g., 1.30 for +30% efficiency)
        """
        if facility is None or facility.facility_type != FacilityType.TRAINING_GROUND:
            return 1.0
        return 1.0 + facility.effect_percentage
    
    def get_injury_recovery_bonus(self, facility: Optional[Facility]) -> float:
        """Calculate medical center injury recovery bonus.
        
        Args:
            facility: Medical center facility
            
        Returns:
            Bonus multiplier (e.g., 1.25 for +25% faster recovery)
        """
        if facility is None or facility.facility_type != FacilityType.MEDICAL_CENTER:
            return 1.0
        return 1.0 + facility.effect_percentage
    
    def get_data_analytics_bonus(self, facility: Optional[Facility]) -> float:
        """Calculate data analytics bonus for scouting and tactics.
        
        Args:
            facility: Data analytics facility
            
        Returns:
            Bonus multiplier (e.g., 1.20 for +20% effectiveness)
        """
        if facility is None or facility.facility_type != FacilityType.DATA_ANALYTICS:
            return 1.0
        return 1.0 + facility.effect_percentage
    
    def get_scouting_network_bonus(self, facility: Optional[Facility]) -> float:
        """Calculate scouting network quality bonus.
        
        Args:
            facility: Scouting network facility
            
        Returns:
            Bonus multiplier (e.g., 1.225 for +22.5% quality)
        """
        if facility is None or facility.facility_type != FacilityType.SCOUTING_NETWORK:
            return 1.0
        return 1.0 + facility.effect_percentage
    
    def get_stadium_capacity(self, facility: Optional[Facility]) -> int:
        """Get stadium capacity.
        
        Args:
            facility: Stadium facility
            
        Returns:
            Stadium capacity (5,000 to 150,000)
        """
        if facility is None or facility.facility_type != FacilityType.STADIUM:
            return 5000
        return facility.stadium_capacity
    
    async def get_facility_effects_summary(
        self, 
        club_id: int
    ) -> dict[str, dict]:
        """Get a summary of all facility effects for a club.
        
        Args:
            club_id: ID of the club
            
        Returns:
            Dictionary with facility type as key and effects dict as value
        """
        facilities = await self.get_all_facilities(club_id)
        
        summary = {}
        for facility in facilities:
            level_config = get_level_config(facility.facility_type, facility.level)
            
            summary[facility.facility_type.value] = {
                "level": facility.level,
                "next_upgrade_cost": facility.upgrade_cost if not facility.is_max_level else 0,
                "weekly_maintenance": facility.weekly_maintenance,
                "effects": level_config.effects,
                "is_max_level": facility.is_max_level,
            }
        
        return summary
    
    async def initialize_club_facilities(self, club_id: int) -> list[Facility]:
        """Initialize default facilities for a new club.
        
        Creates all facility types at level 1 for the club.
        
        Args:
            club_id: ID of the club
            
        Returns:
            List of created facilities
        """
        facilities = []
        
        for facility_type in FacilityType:
            level_config = get_level_config(facility_type, 1)
            
            facility = Facility(
                club_id=club_id,
                facility_type=facility_type,
                level=1,
                upgrade_cost=calculate_upgrade_cost(facility_type, 1),
                weekly_maintenance=level_config.weekly_maintenance,
            )
            
            self.session.add(facility)
            facilities.append(facility)
        
        await self.session.commit()
        return facilities
    
    async def get_upgrade_recommendations(self, club_id: int) -> list[dict]:
        """Get facility upgrade recommendations for a club.
        
        Analyzes current facilities and recommends upgrades based on:
        - Current facility levels
        - Club balance
        - Cost-effectiveness
        
        Args:
            club_id: ID of the club
            
        Returns:
            List of upgrade recommendations sorted by priority
        """
        facilities = await self.get_all_facilities(club_id)
        club = await self.session.get(Club, club_id)
        
        if club is None:
            return []
        
        recommendations = []
        
        for facility in facilities:
            if facility.is_max_level:
                continue
            
            can_upgrade, reason = await self.can_upgrade(club_id, facility.facility_type)
            
            # Calculate priority score (higher = more recommended)
            priority_score = 0
            
            # Lower level = higher priority
            priority_score += (20 - facility.level) * 10
            
            # Lower cost = higher priority
            if facility.upgrade_cost > 0:
                affordability = club.balance / facility.upgrade_cost
                if affordability >= 2.0:
                    priority_score += 50
                elif affordability >= 1.0:
                    priority_score += 30
                elif affordability >= 0.5:
                    priority_score += 10
            
            recommendations.append({
                "facility_type": facility.facility_type.value,
                "current_level": facility.level,
                "upgrade_cost": facility.upgrade_cost,
                "new_maintenance": calculate_maintenance_cost(
                    facility.facility_type, facility.level + 1
                ),
                "can_upgrade": can_upgrade,
                "reason": reason,
                "priority_score": priority_score,
            })
        
        # Sort by priority score (descending)
        recommendations.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return recommendations
    
    async def get_level_config_for_facility(
        self, 
        facility: Facility
    ) -> FacilityLevelConfig:
        """Get detailed configuration for a facility's current level.
        
        Args:
            facility: Facility to get config for
            
        Returns:
            FacilityLevelConfig with all details
        """
        return get_level_config(facility.facility_type, facility.level)
    
    async def get_next_level_config(
        self, 
        facility: Facility
    ) -> Optional[FacilityLevelConfig]:
        """Get configuration for the next level of a facility.
        
        Args:
            facility: Facility to get next level config for
            
        Returns:
            FacilityLevelConfig for next level, or None if at max level
        """
        if facility.is_max_level:
            return None
        return get_level_config(facility.facility_type, facility.level + 1)
