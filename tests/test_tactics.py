#!/usr/bin/env python3
"""战术引擎测试"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.core.models.tactics import (
    PlayerRole, PlayStyle, TacticalInstructions,
    DefensiveLine, PressingIntensity, TeamWidth, Tempo, PassingStyle,
    RoleManager, PlayStyleManager
)
from fm_manager.engine.tactics_engine import TacticsEngine


class TestPlayerRoles:
    """测试球员角色系统"""
    
    def test_all_roles_have_category(self):
        for role in PlayerRole:
            assert role.category in ["attack", "midfield", "wide", "defense", "goalkeeper"]
    
    def test_role_count(self):
        assert len(list(PlayerRole)) >= 25
    
    def test_role_manager_creation(self):
        manager = RoleManager()
        assert manager is not None
    
    def test_get_role_profile(self):
        manager = RoleManager()
        profile = manager.get_role_profile(PlayerRole.PLAYMAKER)
        assert profile is not None
        assert profile.role == PlayerRole.PLAYMAKER
    
    def test_suitable_roles_for_position(self):
        manager = RoleManager()
        from fm_manager.core.models.player import Position
        roles = manager.get_suitable_roles(Position.CAM.value)
        assert PlayerRole.PLAYMAKER in roles or PlayerRole.ADVANCED_PLAYMAKER in roles


class TestPlayStyles:
    """测试比赛风格系统"""
    
    def test_style_count(self):
        assert len(list(PlayStyle)) == 10
    
    def test_style_manager_creation(self):
        manager = PlayStyleManager()
        assert manager is not None
    
    def test_get_style_profile(self):
        manager = PlayStyleManager()
        profile = manager.get_style_profile(PlayStyle.POSSESSION)
        assert profile is not None
        assert profile.instructions.passing_style == PassingStyle.SHORT
    
    def test_possession_style_attributes(self):
        manager = PlayStyleManager()
        profile = manager.get_style_profile(PlayStyle.POSSESSION)
        assert profile.instructions.defensive_line == DefensiveLine.HIGH
        assert profile.instructions.pressing == PressingIntensity.HIGH
        assert profile.instructions.tempo == Tempo.LOW


class TestTacticsEngine:
    """测试战术引擎"""
    
    def setup_method(self):
        self.engine = TacticsEngine()
        self.instructions = TacticalInstructions(
            defensive_line=DefensiveLine.HIGH,
            pressing=PressingIntensity.HIGH,
            width=TeamWidth.NORMAL,
            tempo=Tempo.NORMAL,
            passing_style=PassingStyle.SHORT
        )
    
    def test_passing_bonus_calculation(self):
        bonus = self.engine.calculate_passing_bonus(self.instructions)
        assert 0.7 <= bonus <= 1.3
        assert isinstance(bonus, float)
    
    def test_defensive_bonus_calculation(self):
        bonus = self.engine.calculate_defensive_bonus(self.instructions)
        assert 0.8 <= bonus <= 1.25
        assert isinstance(bonus, float)
    
    def test_attacking_bonus_calculation(self):
        bonus = self.engine.calculate_attacking_bonus(self.instructions)
        assert 0.75 <= bonus <= 1.3
        assert isinstance(bonus, float)
    
    def test_possession_vs_direct_comparison(self):
        possession = TacticalInstructions(
            passing_style=PassingStyle.SHORT,
            tempo=Tempo.LOW
        )
        direct = TacticalInstructions(
            passing_style=PassingStyle.LONG,
            tempo=Tempo.HIGH
        )
        
        possession_bonus = self.engine.calculate_passing_bonus(possession)
        direct_bonus = self.engine.calculate_passing_bonus(direct)
        
        assert possession_bonus > direct_bonus
    
    def test_high_press_defensive_bonus(self):
        high_press = TacticalInstructions(pressing=PressingIntensity.EXTREME)
        low_press = TacticalInstructions(pressing=PressingIntensity.MINIMAL)
        
        high_bonus = self.engine.calculate_defensive_bonus(high_press)
        low_bonus = self.engine.calculate_defensive_bonus(low_press)
        
        assert high_bonus > low_bonus


class TestTacticalInstructions:
    """测试战术指令"""
    
    def test_default_values(self):
        instructions = TacticalInstructions()
        assert instructions.defensive_line == DefensiveLine.MEDIUM
        assert instructions.pressing == PressingIntensity.MEDIUM
        assert instructions.width == TeamWidth.NORMAL
        assert instructions.tempo == Tempo.NORMAL
        assert instructions.passing_style == PassingStyle.MIXED
    
    def test_serialization(self):
        instructions = TacticalInstructions(
            defensive_line=DefensiveLine.HIGH,
            pressing=PressingIntensity.HIGH
        )
        data = instructions.to_dict()
        assert "defensive_line" in data
        assert data["defensive_line"] == DefensiveLine.HIGH.value
    
    def test_deserialization(self):
        data = {
            "defensive_line": "HIGH",
            "pressing": "EXTREME",
            "width": "NORMAL",
            "tempo": "HIGH",
            "passing_style": "SHORT"
        }
        instructions = TacticalInstructions.from_dict(data)
        assert instructions.defensive_line == DefensiveLine.HIGH
        assert instructions.pressing == PressingIntensity.EXTREME


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
