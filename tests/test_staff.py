#!/usr/bin/env python3

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.core.models.staff import StaffRole, StaffEffect


class TestStaffSystem:
    
    def test_staff_role_count(self):
        assert len(list(StaffRole)) == 6
    
    def test_staff_effect_creation(self):
        effect = StaffEffect()
        assert effect.player_development_speed == 1.0
        assert effect.injury_recovery_speed == 1.0
    
    def test_staff_effect_multipliers(self):
        effect = StaffEffect(
            player_development_speed=1.2,
            injury_recovery_speed=1.15
        )
        assert effect.player_development_speed == 1.2
        assert effect.injury_recovery_speed == 1.15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
