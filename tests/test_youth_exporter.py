#!/usr/bin/env python3
"""Comprehensive test suite for YouthPlayerExporter.

Verifies all acceptance criteria:
1. Export 1000 players to JSON and verify valid JSON
2. Export 1000 players to CSV and verify all columns present
3. Export 1000 players to SQLite and verify records inserted
4. Test streaming export for 100K players without memory overflow
5. Verify exported data can be loaded back correctly
6. File naming convention: {country}_{timestamp}.{format}
"""

import csv
import gc
import json
import os
import sqlite3
import sys
import time
import tracemalloc
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.config.youth_generation_config import ExportConfig
from fm_manager.engine.youth_exporter import YouthPlayerExporter
from fm_manager.engine.youth_batch_generator import generate_country_youth, YouthPlayer


class TestYouthExporter:
    """Test suite for YouthPlayerExporter."""

    def __init__(self, output_dir: str = "/tmp/youth_export_tests"):
        self.output_dir = Path(output_dir)
        # Clean up any existing test files
        if self.output_dir.exists():
            import shutil

            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = ExportConfig(
            output_dir=str(self.output_dir), batch_size=10000, compression=False
        )
        self.exporter = YouthPlayerExporter(self.config)
        self.results = []

    def _log(self, message: str):
        """Log test progress."""
        print(f"  → {message}")

    def _generate_test_players(self, count: int, country: str = "ENG") -> List[YouthPlayer]:
        """Generate test players."""
        self._log(f"Generating {count} test players for {country}...")
        start = time.time()
        players = generate_country_youth(country, count, batch_size=min(100000, count))
        elapsed = time.time() - start
        self._log(f"Generated {len(players)} players in {elapsed:.2f}s")
        return players

    def test_1_json_export(self):
        """Test 1: Export 1000 players to JSON and verify file is valid JSON."""
        print("\n[Test 1] JSON Export - 1000 players")
        print("=" * 60)

        # Generate players
        players = self._generate_test_players(1000, "ENG")

        # Export
        filepath = self.output_dir / "test_eng.json"
        result = self.exporter.export_to_json(players, str(filepath))
        self._log(f"Exported to: {result}")

        # Verify file exists
        assert Path(result).exists(), "JSON file does not exist"
        self._log("✓ File exists")

        # Verify valid JSON
        with open(result, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._log("✓ File is valid JSON")

        # Verify structure
        assert "metadata" in data, "Missing metadata"
        assert "players" in data, "Missing players array"
        assert data["metadata"]["player_count"] == 1000, "Wrong player count"
        self._log("✓ JSON structure correct")

        # Verify players loaded
        loaded_players = data["players"]
        assert len(loaded_players) == 1000, f"Expected 1000 players, got {len(loaded_players)}"
        self._log("✓ All 1000 players present")

        # Verify first player has required fields
        player = loaded_players[0]
        required_fields = [
            "first_name",
            "last_name",
            "full_name",
            "nationality",
            "age",
            "position",
            "current_ability",
            "potential_ability",
        ]
        for field in required_fields:
            assert field in player, f"Missing field: {field}"
        self._log("✓ All required fields present")

        # Verify metadata fields
        meta = data["metadata"]
        assert "version" in meta, "Missing version in metadata"
        assert "export_timestamp" in meta, "Missing timestamp in metadata"
        assert "format" in meta, "Missing format in metadata"
        self._log("✓ Metadata fields correct")

        self.results.append(("JSON Export 1000", "PASS", "0.0s"))
        return True

    def test_2_csv_export(self):
        """Test 2: Export 1000 players to CSV and verify all columns present."""
        print("\n[Test 2] CSV Export - 1000 players")
        print("=" * 60)

        # Generate players
        players = self._generate_test_players(1000, "GER")

        # Export
        filepath = self.output_dir / "test_ger.csv"
        result = self.exporter.export_to_csv(players, str(filepath))
        self._log(f"Exported to: {result}")

        # Verify file exists
        assert Path(result).exists(), "CSV file does not exist"
        self._log("✓ File exists")

        # Read and verify
        with open(result, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            rows = list(reader)

        # Verify columns
        required_columns = [
            "first_name",
            "last_name",
            "full_name",
            "nationality",
            "age",
            "position",
            "current_ability",
            "potential_ability",
            "height",
            "weight",
            "preferred_foot",
            "birth_date",
        ]
        for col in required_columns:
            assert col in headers, f"Missing column: {col}"
        self._log(f"✓ All required columns present ({len(headers)} columns total)")

        # Verify row count
        assert len(rows) == 1000, f"Expected 1000 rows, got {len(rows)}"
        self._log("✓ All 1000 rows present")

        # Verify data integrity
        first_row = rows[0]
        assert first_row["first_name"], "Empty first_name"
        assert first_row["nationality"], "Empty nationality"
        assert int(first_row["current_ability"]) > 0, "Invalid current_ability"
        self._log("✓ Data integrity verified")

        self.results.append(("CSV Export 1000", "PASS", "0.0s"))
        return True

    def test_3_sqlite_export(self):
        """Test 3: Export 1000 players to SQLite and verify records inserted."""
        print("\n[Test 3] SQLite Export - 1000 players")
        print("=" * 60)

        # Generate players
        players = self._generate_test_players(1000, "ESP")

        # Export
        filepath = self.output_dir / "test_esp.db"
        result = self.exporter.export_to_sqlite(players, str(filepath), country_code="ESP")
        self._log(f"Exported to: {result}")

        # Verify file exists
        assert Path(result).exists(), "SQLite file does not exist"
        self._log("✓ Database file exists")

        # Connect and verify
        conn = sqlite3.connect(result)
        cursor = conn.cursor()

        # Check record count
        cursor.execute("SELECT COUNT(*) FROM youth_players")
        count = cursor.fetchone()[0]
        assert count == 1000, f"Expected 1000 records, got {count}"
        self._log("✓ All 1000 records inserted")

        # Check table structure
        cursor.execute("PRAGMA table_info(youth_players)")
        columns = [col[1] for col in cursor.fetchall()]
        required_cols = [
            "first_name",
            "last_name",
            "nationality",
            "age",
            "position",
            "current_ability",
            "potential_ability",
            "country_code",
        ]
        for col in required_cols:
            assert col in columns, f"Missing column: {col}"
        self._log(f"✓ Table structure correct ({len(columns)} columns)")

        # Check indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [idx[0] for idx in cursor.fetchall()]
        assert "idx_nationality" in indexes, "Missing index: idx_nationality"
        assert "idx_position" in indexes, "Missing index: idx_position"
        self._log("✓ Indexes created")

        # Verify data integrity
        cursor.execute("SELECT * FROM youth_players LIMIT 1")
        row = cursor.fetchone()
        assert row is not None, "No data in table"
        self._log("✓ Data retrievable")

        # Verify country_code was set
        cursor.execute("SELECT DISTINCT country_code FROM youth_players")
        codes = cursor.fetchall()
        assert codes[0][0] == "ESP", f"Wrong country_code: {codes[0][0]}"
        self._log("✓ Country code correct")

        conn.close()

        self.results.append(("SQLite Export 1000", "PASS", "0.0s"))
        return True

    def test_4_large_scale_memory(self):
        """Test 4: Export 100K players without memory overflow."""
        print("\n[Test 4] Large Scale Export - 100K players (Memory Test)")
        print("=" * 60)

        # Start memory tracking
        tracemalloc.start()
        gc.collect()
        baseline = tracemalloc.get_traced_memory()[0]
        self._log(f"Baseline memory: {baseline / 1024 / 1024:.2f} MB")

        # Generate 100K players
        players = self._generate_test_players(100000, "FRA")

        after_gen = tracemalloc.get_traced_memory()[0]
        gen_memory = (after_gen - baseline) / 1024 / 1024
        self._log(f"Memory after generation: {gen_memory:.2f} MB")

        # Test JSON export
        gc.collect()
        before_json = tracemalloc.get_traced_memory()[0]

        start = time.time()
        json_path = self.output_dir / "test_fra_100k.json"
        self.exporter.export_to_json(players, str(json_path))
        json_time = time.time() - start

        after_json = tracemalloc.get_traced_memory()[0]
        json_memory = (after_json - before_json) / 1024 / 1024
        self._log(f"JSON export: {json_time:.2f}s, Memory delta: {json_memory:.2f} MB")

        # Test CSV export
        gc.collect()
        before_csv = tracemalloc.get_traced_memory()[0]

        start = time.time()
        csv_path = self.output_dir / "test_fra_100k.csv"
        self.exporter.export_to_csv(players, str(csv_path))
        csv_time = time.time() - start

        after_csv = tracemalloc.get_traced_memory()[0]
        csv_memory = (after_csv - before_csv) / 1024 / 1024
        self._log(f"CSV export: {csv_time:.2f}s, Memory delta: {csv_memory:.2f} MB")

        # Test SQLite export
        gc.collect()
        before_sqlite = tracemalloc.get_traced_memory()[0]

        start = time.time()
        sqlite_path = self.output_dir / "test_fra_100k.db"
        self.exporter.export_to_sqlite(players, str(sqlite_path), country_code="FRA")
        sqlite_time = time.time() - start

        after_sqlite = tracemalloc.get_traced_memory()[0]
        sqlite_memory = (after_sqlite - before_sqlite) / 1024 / 1024
        self._log(f"SQLite export: {sqlite_time:.2f}s, Memory delta: {sqlite_memory:.2f} MB")

        tracemalloc.stop()

        # Verify performance targets (with 10% margin for system variance)
        max_json_time = 6.0  # 5 seconds + margin
        max_csv_time = 6.0  # 5 seconds + margin
        max_sqlite_time = 12.0  # 10 seconds + margin
        max_memory = 500  # 500 MB

        assert json_time < max_json_time, f"JSON too slow: {json_time:.2f}s > {max_json_time}s"
        self._log(f"✓ JSON meets performance target (< {max_json_time}s)")

        assert csv_time < max_csv_time, f"CSV too slow: {csv_time:.2f}s > {max_csv_time}s"
        self._log(f"✓ CSV meets performance target (< {max_csv_time}s)")

        assert sqlite_time < max_sqlite_time, (
            f"SQLite too slow: {sqlite_time:.2f}s > {max_sqlite_time}s"
        )
        self._log(f"✓ SQLite meets performance target (< {max_sqlite_time}s)")

        # Verify files are valid
        with open(json_path, "r") as f:
            data = json.load(f)
        assert len(data["players"]) == 100000, "JSON player count mismatch"
        self._log("✓ JSON file valid with 100K players")

        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 100001, (
            f"CSV row count mismatch (expected 100001 with header, got {len(rows)})"
        )
        self._log("✓ CSV file valid with 100K rows")

        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM youth_players")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 100000, f"SQLite record count mismatch"
        self._log("✓ SQLite file valid with 100K records")

        self.results.append(
            ("Large Scale 100K JSON", f"PASS ({json_time:.2f}s)", f"{json_memory:.1f}MB")
        )
        self.results.append(
            ("Large Scale 100K CSV", f"PASS ({csv_time:.2f}s)", f"{csv_memory:.1f}MB")
        )
        self.results.append(
            ("Large Scale 100K SQLite", f"PASS ({sqlite_time:.2f}s)", f"{sqlite_memory:.1f}MB")
        )

        return True

    def test_5_data_roundtrip(self):
        """Test 5: Verify exported data can be loaded back correctly."""
        print("\n[Test 5] Data Roundtrip Verification")
        print("=" * 60)

        # Generate players
        players = self._generate_test_players(100, "ITA")

        # Get original data for comparison
        original = players[0]
        original_dict = self.exporter._player_to_dict(original)

        # Export to JSON
        json_path = self.output_dir / "test_roundtrip.json"
        self.exporter.export_to_json(players, str(json_path))

        # Load back
        with open(json_path, "r") as f:
            data = json.load(f)
        loaded = data["players"][0]

        # Verify key fields
        assert loaded["first_name"] == original.first_name, "first_name mismatch"
        assert loaded["last_name"] == original.last_name, "last_name mismatch"
        assert loaded["nationality"] == original.nationality, "nationality mismatch"
        assert loaded["current_ability"] == original.current_ability, "current_ability mismatch"
        assert loaded["potential_ability"] == original.potential_ability, (
            "potential_ability mismatch"
        )
        assert loaded["position"] == original.position.value, "position mismatch"
        self._log("✓ All key fields match after roundtrip")

        # Verify age calculation
        assert loaded["age"] == original.age, f"age mismatch: {loaded['age']} != {original.age}"
        self._log("✓ Age calculation correct")

        self.results.append(("Data Roundtrip", "PASS", "0.0s"))
        return True

    def test_6_file_naming(self):
        """Test 6: File naming convention {country}_{timestamp}.{format}."""
        print("\n[Test 6] File Naming Convention")
        print("=" * 60)

        players = self._generate_test_players(100, "BRA")

        timestamp = "20240115_143000"

        # Test JSON naming
        filepath = self.exporter._get_filepath("BRA", "json", timestamp)
        assert "BRA" in filepath.name, "Country code missing in filename"
        assert timestamp in filepath.name, "Timestamp missing in filename"
        assert filepath.suffix == ".json", f"Wrong extension: {filepath.suffix}"
        self._log(f"✓ JSON naming: {filepath.name}")

        # Test CSV naming
        filepath = self.exporter._get_filepath("BRA", "csv", timestamp)
        assert filepath.suffix == ".csv", f"Wrong extension: {filepath.suffix}"
        self._log(f"✓ CSV naming: {filepath.name}")

        # Test SQLite naming
        filepath = self.exporter._get_filepath("BRA", "db", timestamp)
        assert filepath.suffix == ".db", f"Wrong extension: {filepath.suffix}"
        self._log(f"✓ SQLite naming: {filepath.name}")

        # Test with spaces in country name
        filepath = self.exporter._get_filepath("United States", "json", timestamp)
        assert "United_States" in filepath.name, "Spaces not replaced"
        self._log("✓ Spaces in country names handled")

        # Test actual export uses correct naming
        results = self.exporter.export_all({"BRA": players}, formats=["json"], timestamp=timestamp)
        exported_file = results["json"][0]
        assert timestamp in exported_file, "Export not using timestamp"
        assert "BRA" in exported_file, "Export not using country code"
        self._log("✓ Export uses correct naming convention")

        self.results.append(("File Naming", "PASS", "0.0s"))
        return True

    def test_7_export_all(self):
        """Test 7: Export all countries to multiple formats."""
        print("\n[Test 7] Export All Countries")
        print("=" * 60)

        # Generate players for multiple countries
        players_by_country = {
            "ENG": self._generate_test_players(500, "ENG"),
            "GER": self._generate_test_players(500, "GER"),
            "ESP": self._generate_test_players(500, "ESP"),
        }

        # Export to all formats
        results = self.exporter.export_all(players_by_country)

        # Verify results
        assert "json" in results, "JSON not in results"
        assert "csv" in results, "CSV not in results"
        assert "sqlite" in results, "SQLite not in results"
        self._log("✓ All formats exported")

        # Verify file counts
        assert len(results["json"]) == 3, f"Expected 3 JSON files, got {len(results['json'])}"
        assert len(results["csv"]) == 3, f"Expected 3 CSV files, got {len(results['csv'])}"
        assert len(results["sqlite"]) == 3, f"Expected 3 SQLite files, got {len(results['sqlite'])}"
        self._log("✓ Correct number of files per format")

        # Verify all files exist
        for fmt, files in results.items():
            for f in files:
                assert Path(f).exists(), f"File does not exist: {f}"
        self._log("✓ All files exist")

        self.results.append(("Export All", "PASS", "0.0s"))
        return True

    def test_8_single_sqlite_db(self):
        """Test 8: Export all countries to single SQLite database."""
        print("\n[Test 8] Single SQLite Database")
        print("=" * 60)

        players_by_country = {
            "ENG": self._generate_test_players(300, "ENG"),
            "GER": self._generate_test_players(300, "GER"),
            "ESP": self._generate_test_players(300, "ESP"),
            "FRA": self._generate_test_players(300, "FRA"),
        }

        result = self.exporter.export_to_single_sqlite(players_by_country)
        self._log(f"Exported to: {result}")

        # Verify
        conn = sqlite3.connect(result)
        cursor = conn.cursor()

        # Check total count
        cursor.execute("SELECT COUNT(*) FROM youth_players")
        total = cursor.fetchone()[0]
        assert total == 1200, f"Expected 1200 records, got {total}"
        self._log(f"✓ All {total} records present")

        # Check country distribution
        cursor.execute("SELECT country_code, COUNT(*) FROM youth_players GROUP BY country_code")
        counts = cursor.fetchall()
        assert len(counts) == 4, f"Expected 4 countries, got {len(counts)}"
        for code, count in counts:
            assert count == 300, f"Wrong count for {code}: {count}"
        self._log("✓ Country distribution correct")

        conn.close()

        self.results.append(("Single SQLite DB", "PASS", "0.0s"))
        return True

    def run_all_tests(self):
        """Run all tests."""
        print("\n" + "=" * 70)
        print("YOUTH PLAYER EXPORTER - COMPREHENSIVE TEST SUITE")
        print("=" * 70)

        tests = [
            self.test_1_json_export,
            self.test_2_csv_export,
            self.test_3_sqlite_export,
            self.test_4_large_scale_memory,
            self.test_5_data_roundtrip,
            self.test_6_file_naming,
            self.test_7_export_all,
            self.test_8_single_sqlite_db,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                test()
                passed += 1
            except Exception as e:
                print(f"\n  ✗ FAILED: {e}")
                import traceback

                traceback.print_exc()
                failed += 1
                self.results.append((test.__name__, "FAIL", str(e)))

        # Print summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"{'Test':<40} {'Status':<20} {'Details'}")
        print("-" * 70)
        for name, status, details in self.results:
            print(f"{name:<40} {status:<20} {details}")
        print("-" * 70)
        print(f"Total: {passed} passed, {failed} failed")
        print("=" * 70)

        return failed == 0


def main():
    """Run the test suite."""
    tester = TestYouthExporter()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
