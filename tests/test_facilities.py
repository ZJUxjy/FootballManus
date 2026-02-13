#!/usr/bin/env python3

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.core.models.facility import (
    FacilityType, calculate_upgrade_cost, calculate_maintenance_cost
)


class TestFacilitySystem:
    
    def test_facility_type_count(self):
        assert len(list(FacilityType)) == 6
    
    def test_upgrade_cost_exponential_growth(self):
        base_cost = 500000
        level_1 = calculate_upgrade_cost(base_cost, 1)
        level_2 = calculate_upgrade_cost(base_cost, 2)
        level_5 = calculate_upgrade_cost(base_cost, 5)
        
        assert level_2 > level_1
        assert level_5 > level_2
        assert level_2 / level_1 == pytest.approx(1.5, rel=0.01)
    
    def test_maintenance_cost_increases_with_level(self):
        cost_1 = calculate_maintenance_cost(FacilityType.YOUTH_ACADEMY, 1)
        cost_10 = calculate_maintenance_cost(FacilityType.YOUTH_ACADEMY, 10)
        cost_20 = calculate_maintenance_cost(FacilityType.YOUTH_ACADEMY, 20)
        
        assert cost_20 > cost_10 > cost_1
    
    def test_youth_academy_effect_scaling(self):
        from fm_manager.core.models.facility import get_level_config
        
        config_1 = get_level_config(FacilityType.YOUTH_ACADEMY, 1)
        config_20 = get_level_config(FacilityType.YOUTH_ACADEMY, 20)
        
        effect_1 = config_1.get_effect("youth_quality")
        effect_20 = config_20.get_effect("youth_quality")
        
        assert effect_20 > effect_1
        assert effect_20 <= 0.70  # Max 70% bonus


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
