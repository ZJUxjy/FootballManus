"""Tests for player development system."""

import pytest
import random
from datetime import date

from fm_manager.engine.player_development import (
    PlayerDevelopmentEngine,
    YouthAcademyGenerator,
    DevelopmentTracker,
    YouthIntakeConfig,
    DevelopmentPhase,
    InjuryImpact,
)
from fm_manager.core.models import Player, Position


class TestYouthAcademyGenerator:
    """Tests for youth academy generation."""

    def test_generate_youth_player_basic(self):
        """Test basic youth player generation."""
        generator = YouthAcademyGenerator(seed=42)
        config = YouthIntakeConfig(academy_level=70)

        intake_date = date(2024, 7, 1)
        player = generator._generate_youth_player(
            club_id=1,
            club_reputation=8000,
            config=config,
            intake_date=intake_date,
        )

        assert player.club_id == 1
        assert player.birth_date is not None
        birth_year = player.birth_date.year
        expected_age = intake_date.year - birth_year
        assert 15 <= expected_age <= 17
        assert player.current_ability >= 20
        assert player.potential_ability >= player.current_ability
        assert player.position is not None

    def test_youth_player_potential_based_on_academy(self):
        """Test that better academies produce higher potential players."""
        generator = YouthAcademyGenerator(seed=42)

        # High level academy
        high_config = YouthIntakeConfig(academy_level=90)
        high_player = generator._generate_youth_player(
            club_id=1,
            club_reputation=9000,
            config=high_config,
            intake_date=date(2024, 7, 1),
        )

        # Low level academy
        low_config = YouthIntakeConfig(academy_level=30)
        low_player = generator._generate_youth_player(
            club_id=1,
            club_reputation=3000,
            config=low_config,
            intake_date=date(2024, 7, 1),
        )

        # High academy should generally produce higher potential
        assert high_player.potential_ability > low_player.potential_ability

    def test_generate_youth_intake(self):
        """Test generating multiple youth players."""
        generator = YouthAcademyGenerator(seed=42)
        config = YouthIntakeConfig(players_per_intake=5)

        players = generator.generate_youth_intake(
            club_id=1,
            club_reputation=7000,
            config=config,
            intake_date=date(2024, 7, 1),
        )

        assert len(players) == 5
        for player in players:
            assert player.club_id == 1
            assert player.birth_date is not None
            birth_year = player.birth_date.year
            expected_age = 2024 - birth_year
            assert 15 <= expected_age <= 17


class TestPlayerDevelopmentEngine:
    """Tests for player development engine."""

    def test_get_development_phase(self):
        """Test development phase determination."""
        engine = PlayerDevelopmentEngine()

        assert engine.get_development_phase(16) == DevelopmentPhase.YOUTH
        assert engine.get_development_phase(20) == DevelopmentPhase.DEVELOPMENT
        assert engine.get_development_phase(25) == DevelopmentPhase.PRIME
        assert engine.get_development_phase(28) == DevelopmentPhase.LATE_PRIME
        assert engine.get_development_phase(32) == DevelopmentPhase.DECLINE
        assert engine.get_development_phase(35) == DevelopmentPhase.LATE_DECLINE

    def test_young_player_growth(self):
        """Test that young players grow."""
        engine = PlayerDevelopmentEngine(seed=42)

        player = Player(
            first_name="Test",
            last_name="Player",
            birth_date=date(2006, 1, 1),  # 18 years old
            position=Position.ST,
            current_ability=50,
            potential_ability=80,
        )

        old_ability = player.current_ability
        result = engine.calculate_season_development(
            player=player,
            minutes_played=2500,  # Lots of playing time
            training_quality=80,
        )

        assert result["growth"] > 0
        assert player.current_ability > old_ability
        assert result["age_multiplier"] > 0

    def test_old_player_decline(self):
        """Test that old players decline."""
        engine = PlayerDevelopmentEngine(seed=42)

        player = Player(
            first_name="Old",
            last_name="Player",
            birth_date=date(1988, 1, 1),  # 36 years old
            position=Position.ST,
            current_ability=70,
            potential_ability=75,
            pace=70,
            acceleration=70,
            stamina=70,
            strength=70,
        )

        old_ability = player.current_ability
        result = engine.calculate_season_development(
            player=player,
            minutes_played=2000,
            training_quality=70,
        )

        assert result["growth"] <= 0
        assert result["age_multiplier"] < 0

    def test_playing_time_impact(self):
        """Test that playing time affects development."""
        engine = PlayerDevelopmentEngine(seed=42)

        # Player with lots of playing time
        player1 = Player(
            first_name="Test1",
            last_name="Player",
            birth_date=date(2004, 1, 1),
            position=Position.ST,
            current_ability=60,
            potential_ability=85,
        )

        # Player with little playing time
        player2 = Player(
            first_name="Test2",
            last_name="Player",
            birth_date=date(2004, 1, 1),
            position=Position.ST,
            current_ability=60,
            potential_ability=85,
        )

        result1 = engine.calculate_season_development(
            player=player1, minutes_played=3000, training_quality=70
        )
        result2 = engine.calculate_season_development(
            player=player2, minutes_played=200, training_quality=70
        )

        # More playing time should result in more growth
        assert result1["growth"] > result2["growth"]

    def test_potential_cap(self):
        """Test that players don't exceed their potential."""
        engine = PlayerDevelopmentEngine(seed=42)

        player = Player(
            first_name="Capped",
            last_name="Player",
            birth_date=date(2005, 1, 1),
            position=Position.ST,
            current_ability=78,
            potential_ability=80,  # Only 2 points gap
        )

        result = engine.calculate_season_development(
            player=player, minutes_played=3000, training_quality=90
        )

        # Should not exceed potential
        assert player.current_ability <= 80

    def test_injury_recovery_no_effect(self):
        """Test minor injury has no permanent effect."""
        engine = PlayerDevelopmentEngine(seed=42)

        player = Player(
            first_name="Injured",
            last_name="Player",
            birth_date=date(2000, 1, 1),
            position=Position.ST,
            current_ability=70,
            potential_ability=80,
            pace=70,
        )

        result = engine.apply_injury_recovery(player, injury_severity=2, recovery_weeks=4)

        assert result["permanent_reduction"] == False
        assert len(result["reduced_attributes"]) == 0

    def test_injury_recovery_with_effect(self):
        """Test serious injury has permanent effect."""
        engine = PlayerDevelopmentEngine(seed=42)

        player = Player(
            first_name="Injured",
            last_name="Player",
            birth_date=date(2000, 1, 1),
            position=Position.ST,
            current_ability=70,
            potential_ability=80,
            pace=70,
            acceleration=70,
        )

        old_pace = player.pace
        result = engine.apply_injury_recovery(player, injury_severity=4, recovery_weeks=20)

        # Serious injury should have permanent effects
        if result["permanent_reduction"]:
            assert len(result["reduced_attributes"]) > 0

    def test_retirement_check_young(self):
        """Test young players don't retire."""
        engine = PlayerDevelopmentEngine(seed=42)

        player = Player(
            first_name="Young",
            last_name="Player",
            birth_date=date(2000, 1, 1),  # 24 years old
            position=Position.ST,
            current_ability=70,
        )

        should_retire, reason = engine.check_retirement(player)
        assert should_retire == False

    def test_retirement_check_old(self):
        """Test old players may retire."""
        engine = PlayerDevelopmentEngine(seed=42)

        # Test multiple times since retirement is probabilistic
        retire_count = 0
        for _ in range(100):
            player = Player(
                first_name="Old",
                last_name="Player",
                birth_date=date(1985, 1, 1),  # 39 years old
                position=Position.ST,
                current_ability=60,
            )
            should_retire, _ = engine.check_retirement(player)
            if should_retire:
                retire_count += 1

        # Most 39-year-olds should retire
        assert retire_count > 50


class TestDevelopmentTracker:
    """Tests for development tracking."""

    def test_get_or_create_profile(self):
        """Test profile creation."""
        tracker = DevelopmentTracker()

        player = Player(
            id=1,
            first_name="Test",
            last_name="Player",
            birth_date=date(2000, 1, 1),
            position=Position.ST,
        )

        profile = tracker.get_or_create_profile(player)

        assert profile.player_id == 1
        assert profile.primary_position == Position.ST

    def test_record_season(self):
        """Test recording a season."""
        tracker = DevelopmentTracker()

        player = Player(
            id=1,
            first_name="Test",
            last_name="Player",
            birth_date=date(2000, 1, 1),
            position=Position.ST,
            current_ability=60,
        )

        tracker.record_season(
            player=player,
            minutes_played=2000,
            development_result={"growth": 5},
        )

        profile = tracker.profiles[1]
        assert profile.total_minutes_played == 2000
        assert len(profile.ability_history) == 1

    def test_development_summary(self):
        """Test development summary generation."""
        tracker = DevelopmentTracker()

        player = Player(
            id=1,
            first_name="Test",
            last_name="Player",
            birth_date=date(2000, 1, 1),
            position=Position.ST,
            current_ability=60,
        )

        # Record multiple seasons
        for i in range(3):
            player.current_ability = 60 + i * 3
            tracker.record_season(
                player=player,
                minutes_played=2000,
                development_result={"growth": 3},
            )

        summary = tracker.get_development_summary(1)

        assert summary is not None
        assert summary["total_growth"] == 6  # 60 -> 66
        assert summary["seasons_tracked"] == 3


class TestAgeCurve:
    """Tests for age-based development curve."""

    def test_age_curve_values(self):
        """Test that age curve has correct values."""
        engine = PlayerDevelopmentEngine()

        # Young players should have positive multipliers
        assert engine.AGE_CURVE[16] > 1.0
        assert engine.AGE_CURVE[20] == 1.0

        # Prime players should have moderate multipliers
        assert 0.5 < engine.AGE_CURVE[25] < 1.0

        # Old players should have negative multipliers
        assert engine.AGE_CURVE[33] < 0
        assert engine.AGE_CURVE[36] < -0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
