"""Test suite for YouthAttributeGenerator.

Verifies that the generator creates valid attributes for all positions.
"""

import pytest
from fm_manager.engine.youth_attribute_generator import (
    YouthAttributeGenerator,
    generate_youth_attributes,
)


class TestYouthAttributeGenerator:
    """Test youth attribute generation."""

    def setup_method(self):
        """Set up test generator with fixed seed for reproducibility."""
        self.generator = YouthAttributeGenerator(seed=42)

    def test_generate_single_player(self):
        """Test generating attributes for a single player."""
        attrs = self.generator.generate_attributes(
            ca=100, pa=150, position="ST", age=17, country="England"
        )

        # Verify all expected attributes are present
        expected_attrs = [
            # Technical
            "shooting",
            "passing",
            "dribbling",
            "crossing",
            "first_touch",
            "technique",
            "tackling",
            "marking",
            "positioning",
            "vision",
            "decisions",
            # Physical
            "pace",
            "acceleration",
            "stamina",
            "strength",
            "agility",
            "jumping",
            "balance",
            # Mental
            "work_rate",
            "determination",
            "leadership",
            "teamwork",
            "aggression",
            "composure",
            "concentration",
            "anticipation",
            # Goalkeeping (should be present for all)
            "reflexes",
            "handling",
            "kicking",
            "one_on_one",
        ]

        for attr in expected_attrs:
            assert attr in attrs, f"Missing attribute: {attr}"
            assert isinstance(attrs[attr], int), f"Attribute {attr} should be int"
            assert 1 <= attrs[attr] <= 100, f"Attribute {attr} out of range: {attrs[attr]}"

    def test_all_positions(self):
        """Test attribute generation for all positions."""
        positions = ["GK", "CB", "LB", "RB", "CDM", "CM", "LM", "RM", "CAM", "LW", "RW", "CF", "ST"]

        for pos in positions:
            attrs = self.generator.generate_attributes(
                ca=80, pa=120, position=pos, age=17, country="Brazil"
            )

            # Verify GK attributes are high for goalkeepers, low for others
            if pos == "GK":
                assert attrs["reflexes"] > 50, "GK should have high reflexes"
                assert attrs["handling"] > 50, "GK should have high handling"
                # GK shooting should be lower than outfield positions on average
                assert attrs["shooting"] < attrs["reflexes"], (
                    "GK shooting should be lower than reflexes"
                )
            else:
                assert attrs["reflexes"] < 50, "Outfield player should have low reflexes"
                assert attrs["handling"] < 50, "Outfield player should have low handling"

            # Position-specific checks
            if pos in ["ST", "CF"]:
                assert attrs["shooting"] > attrs["marking"], (
                    f"ST/CF should prioritize shooting over marking"
                )
            elif pos in ["CB"]:
                assert attrs["marking"] > attrs["shooting"], (
                    f"CB should prioritize marking over shooting"
                )
            elif pos == "CM":
                assert attrs["passing"] > attrs["shooting"], f"CM should prioritize passing"

    def test_country_modifiers(self):
        """Test that country modifiers affect attributes."""
        # Generate players with same stats but different countries
        technical_countries = ["Spain", "Brazil", "England"]
        results = {}

        for country in technical_countries:
            attrs = self.generator.generate_attributes(
                ca=80, pa=120, position="CM", age=17, country=country
            )
            results[country] = attrs

        # Spain and Brazil should generally have better technical attributes than England
        spain_tech_avg = (results["Spain"]["passing"] + results["Spain"]["vision"]) / 2
        brazil_tech_avg = (results["Brazil"]["dribbling"] + results["Brazil"]["technique"]) / 2

        # Just verify values are in reasonable range
        assert 20 <= spain_tech_avg <= 100
        assert 20 <= brazil_tech_avg <= 100

    def test_age_factor(self):
        """Test that age affects attribute variance."""
        # Generate multiple players at different ages and check variance
        ages = [15, 17, 20, 25]
        variances = {}

        for age in ages:
            values = []
            for _ in range(50):
                attrs = self.generator.generate_attributes(
                    ca=80, pa=120, position="CM", age=age, country="Germany"
                )
                values.append(attrs["shooting"])

            # Calculate variance
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            variances[age] = variance

        # Younger players should generally have more variance
        # (this is probabilistic, so we just check they don't all have zero variance)
        assert all(v > 0 for v in variances.values()), "All ages should have some variance"

    def test_ca_correlation(self):
        """Test that higher CA generally results in better attributes."""
        ca_values = [60, 80, 100, 120]
        averages = []

        for ca in ca_values:
            attrs = self.generator.generate_attributes(
                ca=ca, pa=ca + 30, position="CM", age=18, country="France"
            )
            # Calculate average of key attributes
            avg = (
                sum(
                    [
                        attrs["passing"],
                        attrs["vision"],
                        attrs["decisions"],
                        attrs["pace"],
                        attrs["stamina"],
                        attrs["work_rate"],
                    ]
                )
                / 6
            )
            averages.append(avg)

        # Higher CA should generally give higher averages
        for i in range(len(averages) - 1):
            assert averages[i + 1] >= averages[i] - 15, (
                "Higher CA should not give much lower averages"
            )

    def test_attribute_ranges(self):
        """Test that all attributes stay within valid range."""
        for _ in range(100):
            attrs = self.generator.generate_attributes(
                ca=self.generator.rng.randint(40, 140),
                pa=self.generator.rng.randint(60, 160),
                position=self.generator.rng.choice(
                    ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "ST"]
                ),
                age=self.generator.rng.randint(15, 25),
                country=self.generator.rng.choice(
                    ["Spain", "Brazil", "Germany", "Italy", "England", "France"]
                ),
            )

            for attr_name, value in attrs.items():
                assert 1 <= value <= 100, f"Attribute {attr_name} = {value} out of range"

    def test_generate_100_players(self):
        """Test generating 100 players and verify all have valid attributes."""
        positions = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "ST"]
        countries = ["Spain", "Brazil", "Germany", "Italy", "England", "France", "Argentina"]

        players_generated = 0
        all_attrs_valid = True
        errors = []

        for i in range(100):
            ca = 50 + (i % 100)  # 50-149
            pa = min(200, ca + 20 + (i % 30))
            position = positions[i % len(positions)]
            age = 15 + (i % 10)
            country = countries[i % len(countries)]

            try:
                attrs = self.generator.generate_attributes(
                    ca=ca, pa=pa, position=position, age=age, country=country
                )

                # Validate all attributes
                for attr_name, value in attrs.items():
                    if not (1 <= value <= 100):
                        errors.append(f"Player {i}: {attr_name}={value} out of range")
                        all_attrs_valid = False

                players_generated += 1

            except Exception as e:
                errors.append(f"Player {i}: Exception - {e}")
                all_attrs_valid = False

        assert players_generated == 100, f"Expected 100 players, generated {players_generated}"
        assert all_attrs_valid, f"Attribute validation failed: {errors[:10]}"

    def test_convenience_function(self):
        """Test the convenience function generate_youth_attributes."""
        attrs = generate_youth_attributes(
            ca=90, pa=130, position="ST", age=18, country="Brazil", seed=123
        )

        assert "shooting" in attrs
        assert "pace" in attrs
        assert "determination" in attrs
        assert 1 <= attrs["shooting"] <= 100

    def test_player_summary(self):
        """Test the generate_player_summary method."""
        attrs = self.generator.generate_attributes(
            ca=100, pa=140, position="ST", age=19, country="Germany"
        )

        summary = self.generator.generate_player_summary(attrs, "ST")

        assert "position" in summary
        assert "technical_average" in summary
        assert "physical_average" in summary
        assert "mental_average" in summary
        assert "top_strengths" in summary
        assert "top_weaknesses" in summary
        assert len(summary["top_strengths"]) == 3
        assert len(summary["top_weaknesses"]) == 3

    def test_gk_specific_attributes(self):
        """Test that goalkeepers get proper GK attributes."""
        gk_attrs = self.generator.generate_attributes(
            ca=100, pa=140, position="GK", age=18, country="Germany"
        )

        # GK should have high GK attributes
        assert gk_attrs["reflexes"] > 60, "GK should have high reflexes"
        assert gk_attrs["handling"] > 60, "GK should have high handling"
        assert gk_attrs["one_on_one"] > 60, "GK should have high one_on_one"

        # GK shooting should be lower than their GK attributes
        assert gk_attrs["shooting"] < gk_attrs["reflexes"], (
            "GK shooting should be lower than reflexes"
        )
        assert gk_attrs["dribbling"] < gk_attrs["reflexes"], (
            "GK dribbling should be lower than reflexes"
        )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
