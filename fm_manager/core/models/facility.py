"""Facility model definitions for FM Manager.

Handles club facilities including youth academy, training ground,
data analytics, medical center, scouting network, and stadium.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum as PyEnum
from typing import Optional, TYPE_CHECKING, Dict

from sqlalchemy import ForeignKey, Integer, Enum, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fm_manager.core.database import Base

if TYPE_CHECKING:
    from fm_manager.core.models.club import Club


class FacilityType(PyEnum):
    """Types of club facilities that can be upgraded."""
    YOUTH_ACADEMY = "youth_academy"          # 青训学院 - affects youth player quality
    TRAINING_GROUND = "training_ground"       # 训练场 - affects training efficiency
    DATA_ANALYTICS = "data_analytics"         # 数据分析 - affects scouting & tactics
    MEDICAL_CENTER = "medical_center"         # 医疗中心 - affects injury recovery
    SCOUTING_NETWORK = "scouting_network"     # 球探网络 - affects scouting quality
    STADIUM = "stadium"                       # 球场 - affects capacity & match income


@dataclass
class FacilityLevelConfig:
    """Configuration for a facility level.
    
    Attributes:
        level: Facility level (1-20)
        upgrade_cost: Cost to upgrade TO this level (from level-1)
        weekly_maintenance: Weekly maintenance cost
        effects: Dictionary of effect bonuses (e.g., {"youth_quality": 0.035})
        description: Human-readable description of this level
    """
    level: int
    upgrade_cost: int
    weekly_maintenance: int
    effects: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    
    def get_effect(self, effect_type: str) -> float:
        """Get the value of a specific effect type."""
        return self.effects.get(effect_type, 0.0)


class Facility(Base):
    """Facility entity representing a club's upgradeable facility.
    
    Each club has one facility record per facility type.
    """
    
    __tablename__ = "facilities"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Foreign key to club
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"), 
        nullable=False,
        index=True
    )
    
    # Facility type
    facility_type: Mapped[FacilityType] = mapped_column(
        Enum(FacilityType), 
        nullable=False
    )
    
    # Current level (1-20, where 1 is basic, 20 is world-class)
    level: Mapped[int] = mapped_column(
        Integer, 
        default=1,
        nullable=False
    )
    
    # Upgrade cost for next level (calculated dynamically)
    upgrade_cost: Mapped[int] = mapped_column(
        Integer, 
        default=0,
        nullable=False
    )
    
    # Weekly maintenance cost
    weekly_maintenance: Mapped[int] = mapped_column(
        Integer, 
        default=0,
        nullable=False
    )
    
    # Relationships
    club: Mapped["Club"] = relationship(back_populates="facilities")
    
    def __repr__(self) -> str:
        return f"<Facility(id={self.id}, type={self.facility_type.value}, level={self.level})>"
    
    @property
    def is_max_level(self) -> bool:
        """Check if facility is at maximum level."""
        return self.level >= 20
    
    @property
    def effect_percentage(self) -> float:
        """Calculate effect percentage based on facility type and level.
        
        Returns:
            Percentage bonus (e.g., 0.35 for 35%)
        """
        # Linear interpolation from level 1 (0%) to level 20 (max)
        max_effects = {
            FacilityType.YOUTH_ACADEMY: 0.70,      # +0% to +70%
            FacilityType.TRAINING_GROUND: 0.60,    # +0% to +60%
            FacilityType.MEDICAL_CENTER: 0.50,     # +0% to +50%
            FacilityType.DATA_ANALYTICS: 0.40,     # +0% to +40%
            FacilityType.SCOUTING_NETWORK: 0.45,   # +0% to +45%
            FacilityType.STADIUM: 1.0,             # Special: capacity-based
        }
        max_effect = max_effects.get(self.facility_type, 0.0)
        # Level 1 = 0%, Level 20 = max_effect
        return ((self.level - 1) / 19) * max_effect
    
    @property
    def stadium_capacity(self) -> int:
        """Get stadium capacity if this is a stadium facility.
        
        Returns:
            Capacity ranging from 5,000 (level 1) to 150,000 (level 20)
        """
        if self.facility_type != FacilityType.STADIUM:
            return 0
        # Linear interpolation: 5,000 to 150,000
        min_capacity = 5000
        max_capacity = 150000
        return min_capacity + int((self.level - 1) / 19 * (max_capacity - min_capacity))


# Static configuration data for facility levels
FACILITY_BASE_CONFIGS: dict[FacilityType, dict] = {
    FacilityType.YOUTH_ACADEMY: {
        "base_cost": 1_000_000,      # 1M base cost
        "base_maintenance": 50_000,   # 50K weekly maintenance
        "max_effect": 0.70,           # +70% youth quality at max
        "effect_key": "youth_quality",
    },
    FacilityType.TRAINING_GROUND: {
        "base_cost": 800_000,
        "base_maintenance": 40_000,
        "max_effect": 0.60,
        "effect_key": "training_efficiency",
    },
    FacilityType.DATA_ANALYTICS: {
        "base_cost": 600_000,
        "base_maintenance": 30_000,
        "max_effect": 0.40,
        "effect_key": "data_quality",
    },
    FacilityType.MEDICAL_CENTER: {
        "base_cost": 700_000,
        "base_maintenance": 35_000,
        "max_effect": 0.50,
        "effect_key": "injury_recovery",
    },
    FacilityType.SCOUTING_NETWORK: {
        "base_cost": 500_000,
        "base_maintenance": 25_000,
        "max_effect": 0.45,
        "effect_key": "scouting_quality",
    },
    FacilityType.STADIUM: {
        "base_cost": 5_000_000,
        "base_maintenance": 200_000,
        "max_effect": 1.0,            # Stadium uses capacity, not percentage
        "effect_key": "stadium_capacity",
    },
}


def get_facility_config(facility_type: FacilityType) -> dict:
    """Get base configuration for a facility type."""
    return FACILITY_BASE_CONFIGS.get(facility_type, {
        "base_cost": 500_000,
        "base_maintenance": 25_000,
        "max_effect": 0.30,
        "effect_key": "generic_effect",
    })


def calculate_upgrade_cost(facility_type: FacilityType, current_level: int) -> int:
    """Calculate upgrade cost for next level.
    
    Formula: base_cost * (1.5 ^ current_level)
    
    Args:
        facility_type: Type of facility
        current_level: Current facility level (1-19)
        
    Returns:
        Cost to upgrade to next level
    """
    if current_level >= 20:
        return 0
    
    config = get_facility_config(facility_type)
    base_cost = config["base_cost"]
    
    # Formula: base_cost * (1.5 ^ current_level)
    import math
    cost = int(base_cost * math.pow(1.5, current_level))
    
    return cost


def calculate_maintenance_cost(facility_type: FacilityType, level: int) -> int:
    """Calculate weekly maintenance cost for a facility level.
    
    Maintenance increases linearly with level.
    
    Args:
        facility_type: Type of facility
        level: Current facility level (1-20)
        
    Returns:
        Weekly maintenance cost
    """
    config = get_facility_config(facility_type)
    base_maintenance = config["base_maintenance"]
    
    # Linear increase: base * (1 + (level - 1) / 19 * 1.5)
    # Level 1 = base, Level 20 = base * 2.5
    multiplier = 1.0 + ((level - 1) / 19) * 1.5
    
    return int(base_maintenance * multiplier)


def get_level_config(facility_type: FacilityType, level: int) -> FacilityLevelConfig:
    """Get complete configuration for a specific facility level.
    
    Args:
        facility_type: Type of facility
        level: Target level (1-20)
        
    Returns:
        FacilityLevelConfig with all calculated values
    """
    config = get_facility_config(facility_type)
    
    # Calculate upgrade cost (to reach this level from level-1)
    if level == 1:
        upgrade_cost = 0  # No cost for level 1 (starting level)
    else:
        upgrade_cost = calculate_upgrade_cost(facility_type, level - 1)
    
    # Calculate maintenance
    weekly_maintenance = calculate_maintenance_cost(facility_type, level)
    
    # Calculate effect at this level
    if facility_type == FacilityType.STADIUM:
        # Stadium uses capacity, not percentage
        min_capacity = 5000
        max_capacity = 150000
        capacity = min_capacity + int((level - 1) / 19 * (max_capacity - min_capacity))
        effects = {"stadium_capacity": float(capacity)}
    else:
        max_effect = config["max_effect"]
        effect_value = ((level - 1) / 19) * max_effect
        effects = {config["effect_key"]: effect_value}
    
    # Generate description
    descriptions = {
        FacilityType.YOUTH_ACADEMY: [
            "Basic", "Poor", "Below Average", "Average", "Adequate",
            "Good", "Very Good", "Excellent", "Superb", "Fantastic",
            "State of the Art", "State of the Art", "State of the Art",
            "State of the Art", "State of the Art", "State of the Art",
            "State of the Art", "State of the Art", "State of the Art",
            "Legendary"
        ],
        FacilityType.TRAINING_GROUND: [
            "Basic", "Poor", "Below Average", "Average", "Adequate",
            "Good", "Very Good", "Excellent", "Superb", "Fantastic",
            "State of the Art", "State of the Art", "State of the Art",
            "State of the Art", "State of the Art", "State of the Art",
            "State of the Art", "State of the Art", "State of the Art",
            "Legendary"
        ],
    }
    
    type_descriptions = descriptions.get(facility_type, [
        "Basic", "Poor", "Below Average", "Average", "Adequate",
        "Good", "Very Good", "Excellent", "Superb", "Fantastic",
        "State of the Art", "State of the Art", "State of the Art",
        "State of the Art", "State of the Art", "State of the Art",
        "State of the Art", "State of the Art", "State of the Art",
        "Legendary"
    ])
    
    description = type_descriptions[level - 1] if level <= len(type_descriptions) else "Elite"
    
    return FacilityLevelConfig(
        level=level,
        upgrade_cost=upgrade_cost,
        weekly_maintenance=weekly_maintenance,
        effects=effects,
        description=description
    )
