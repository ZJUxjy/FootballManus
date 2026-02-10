"""Youth Player Export System.

Comprehensive export functionality for youth players to multiple formats:
- JSON: Streaming export for large datasets
- CSV: Chunked writing with proper escaping
- SQLite: Bulk insert with batch optimization

Performance targets:
- 100K players to JSON: < 5 seconds
- 100K players to CSV: < 5 seconds
- 100K players to SQLite: < 10 seconds
- Memory usage: < 500MB during export
"""

import csv
import gzip
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union

from fm_manager.config.youth_generation_config import ExportConfig
from fm_manager.engine.youth_batch_generator import YouthPlayer


def _json_dumps(obj) -> str:
    """Serialize object to JSON string."""
    return json.dumps(obj, ensure_ascii=False)


class YouthPlayerExporter:
    """Export youth players to multiple formats with streaming and batch optimization.

    Handles large datasets efficiently using streaming JSON, chunked CSV writing,
    and bulk SQLite inserts. Memory usage is bounded by batch_size.

    Attributes:
        config: ExportConfig with formats, output_dir, batch_size, compression settings
        output_dir: Path object for output directory
    """

    # CSV column headers for consistent ordering
    CSV_COLUMNS = [
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
        # Technical attributes
        "pace",
        "acceleration",
        "stamina",
        "strength",
        "shooting",
        "passing",
        "dribbling",
        "crossing",
        "first_touch",
        "tackling",
        "marking",
        "positioning",
        "vision",
        "decisions",
        # Goalkeeping
        "reflexes",
        "handling",
        "kicking",
        "one_on_one",
        # Mental
        "work_rate",
        "determination",
        "leadership",
        "teamwork",
        "aggression",
        # Additional technical from attributes dict
        "finishing",
        "long_shots",
        "heading",
        "free_kicks",
        "penalty_taking",
        "corners",
        "throw_ins",
        "technique",
        "flair",
        "composure",
    ]

    # SQLite table schema
    SQLITE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS youth_players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        full_name TEXT NOT NULL,
        nationality TEXT NOT NULL,
        age INTEGER NOT NULL,
        position TEXT NOT NULL,
        current_ability INTEGER NOT NULL,
        potential_ability INTEGER NOT NULL,
        height INTEGER,
        weight INTEGER,
        preferred_foot TEXT,
        birth_date TEXT,
        -- Technical attributes
        pace INTEGER, acceleration INTEGER, stamina INTEGER, strength INTEGER,
        shooting INTEGER, passing INTEGER, dribbling INTEGER, crossing INTEGER, first_touch INTEGER,
        tackling INTEGER, marking INTEGER, positioning INTEGER, vision INTEGER, decisions INTEGER,
        -- Goalkeeping
        reflexes INTEGER, handling INTEGER, kicking INTEGER, one_on_one INTEGER,
        -- Mental
        work_rate TEXT, determination INTEGER, leadership INTEGER, teamwork INTEGER, aggression INTEGER,
        -- Additional attributes
        finishing INTEGER, long_shots INTEGER, heading INTEGER, free_kicks INTEGER, penalty_taking INTEGER,
        corners INTEGER, throw_ins INTEGER, technique INTEGER, flair INTEGER, composure INTEGER,
        -- Metadata
        export_timestamp TEXT NOT NULL,
        country_code TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_nationality ON youth_players(nationality);
    CREATE INDEX IF NOT EXISTS idx_position ON youth_players(position);
    CREATE INDEX IF NOT EXISTS idx_ca ON youth_players(current_ability);
    CREATE INDEX IF NOT EXISTS idx_pa ON youth_players(potential_ability);
    CREATE INDEX IF NOT EXISTS idx_country_code ON youth_players(country_code);
    """

    def __init__(self, config: ExportConfig):
        """Initialize exporter with configuration.

        Args:
            config: ExportConfig with formats, output_dir, batch_size, compression
        """
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_filepath(self, country: str, ext: str, timestamp: Optional[str] = None) -> Path:
        """Generate filepath with country and timestamp.

        Format: {country}_{timestamp}.{ext}

        Args:
            country: Country code or name
            ext: File extension (json, csv, db)
            timestamp: Optional timestamp string, defaults to current time

        Returns:
            Path object for the file
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        safe_country = country.replace(" ", "_").replace("/", "_")
        filename = f"{safe_country}_{timestamp}.{ext}"

        if self.config.compression and ext == "json":
            filename += ".gz"
        elif self.config.compression and ext == "csv":
            filename += ".gz"

        return self.output_dir / filename

    def _player_to_dict(self, player: YouthPlayer, include_attributes: bool = True) -> Dict:
        """Convert YouthPlayer to dictionary for serialization.

        Args:
            player: YouthPlayer to convert
            include_attributes: Whether to include all attributes from attributes dict

        Returns:
            Dictionary representation of player
        """
        data = {
            "first_name": player.first_name,
            "last_name": player.last_name,
            "full_name": player.full_name,
            "nationality": player.nationality,
            "age": player.age,
            "position": player.position.value
            if hasattr(player.position, "value")
            else str(player.position),
            "current_ability": player.current_ability,
            "potential_ability": player.potential_ability,
            "height": player.height,
            "weight": player.weight,
            "preferred_foot": player.preferred_foot.value
            if hasattr(player.preferred_foot, "value")
            else str(player.preferred_foot),
            "birth_date": player.birth_date.isoformat(),
        }

        if include_attributes and player.attributes:
            # Merge attributes dict into main dict
            for key, value in player.attributes.items():
                if key not in data:
                    data[key] = value

        return data

    def _batched(self, items: List, batch_size: int) -> Generator[List, None, None]:
        """Yield batches of items.

        Args:
            items: List to batch
            batch_size: Size of each batch

        Yields:
            Batches of items
        """
        for i in range(0, len(items), batch_size):
            yield items[i : i + batch_size]

    def export_to_json(
        self,
        players: List[YouthPlayer],
        filepath: Union[str, Path],
        batch_size: Optional[int] = None,
    ) -> str:
        """Stream players to JSON file in batches.

        Uses streaming JSON writing to handle large datasets without loading
        everything into memory. Writes metadata header and player array.

        Game-readable format:
        {
            "metadata": {
                "version": "1.0",
                "export_timestamp": "2024-01-15T10:30:00",
                "player_count": 100000,
                "format": "youth_players"
            },
            "players": [...]
        }

        Args:
            players: List of YouthPlayer objects to export
            filepath: Output file path
            batch_size: Players per batch (defaults to config.batch_size)

        Returns:
            Absolute path to exported file

        Raises:
            ValueError: If players list is empty
            IOError: If file cannot be written
        """
        if not players:
            raise ValueError("Cannot export empty player list")

        batch_size = batch_size or self.config.batch_size
        filepath = Path(filepath)

        # Determine if we need compression
        use_compression = filepath.suffix == ".gz" or self.config.compression

        metadata = {
            "metadata": {
                "version": "1.0",
                "export_timestamp": datetime.now().isoformat(),
                "player_count": len(players),
                "format": "youth_players",
                "source": "fm_manager_youth_exporter",
            }
        }

        start_time = time.time()

        # Open file with optional gzip compression
        if use_compression:
            f = gzip.open(filepath, "wt", encoding="utf-8")
        else:
            f = open(filepath, "w", encoding="utf-8")

        try:
            with f:
                f.write(_json_dumps(metadata)[0:-1])
                f.write(',\n  "players": [\n')

                first_player = True
                for batch in self._batched(players, batch_size):
                    batch_dicts = [self._player_to_dict(player) for player in batch]
                    batch_json = _json_dumps(batch_dicts)
                    batch_json = batch_json[1:-1]
                    if not first_player:
                        f.write(",")
                    f.write("\n    ")
                    f.write(batch_json.replace("], [", "],\n    ["))
                    first_player = False

                f.write("\n  ]\n}")

        except Exception as e:
            # Clean up partial file on error
            if filepath.exists():
                filepath.unlink()
            raise IOError(f"Failed to export to JSON: {e}")

        elapsed = time.time() - start_time
        print(f"Exported {len(players)} players to JSON in {elapsed:.2f}s")

        return str(filepath.absolute())

    def export_to_csv(
        self, players: List[YouthPlayer], filepath: str, batch_size: Optional[int] = None
    ) -> str:
        """Export players to CSV with headers.

        Uses chunked writing with proper CSV escaping. All special characters
        in names and data are properly escaped following RFC 4180.

        Args:
            players: List of YouthPlayer objects to export
            filepath: Output file path
            batch_size: Players per batch (defaults to config.batch_size)

        Returns:
            Absolute path to exported file

        Raises:
            ValueError: If players list is empty
            IOError: If file cannot be written
        """
        if not players:
            raise ValueError("Cannot export empty player list")

        batch_size = batch_size or self.config.batch_size
        filepath = Path(filepath)

        # Determine columns (intersection of CSV_COLUMNS and available data)
        sample_dict = self._player_to_dict(players[0])
        columns = [col for col in self.CSV_COLUMNS if col in sample_dict]

        # Add any additional keys from attributes that aren't in CSV_COLUMNS
        if players[0].attributes:
            for key in players[0].attributes.keys():
                if key not in columns:
                    columns.append(key)

        use_compression = filepath.suffix == ".gz" or self.config.compression
        start_time = time.time()

        # Open file with optional compression
        if use_compression:
            f = gzip.open(filepath, "wt", encoding="utf-8", newline="")
        else:
            f = open(filepath, "w", encoding="utf-8", newline="")

        try:
            with f:
                writer = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()

                # Write in batches
                for batch in self._batched(players, batch_size):
                    rows = []
                    for player in batch:
                        player_dict = self._player_to_dict(player)
                        # Ensure all columns exist (use None for missing)
                        row = {col: player_dict.get(col, None) for col in columns}
                        rows.append(row)
                    writer.writerows(rows)

        except Exception as e:
            if filepath.exists():
                filepath.unlink()
            raise IOError(f"Failed to export to CSV: {e}")

        elapsed = time.time() - start_time
        print(f"Exported {len(players)} players to CSV in {elapsed:.2f}s")

        return str(filepath.absolute())

    def export_to_sqlite(
        self,
        players: List[YouthPlayer],
        db_path: str,
        batch_size: Optional[int] = None,
        country_code: Optional[str] = None,
    ) -> str:
        """Bulk insert players to SQLite database.

        Creates the database and table if they don't exist, then performs
        bulk inserts in batches for optimal performance. Uses transaction
        wrapping for each batch to minimize commit overhead.

        Args:
            players: List of YouthPlayer objects to export
            db_path: Path to SQLite database file
            batch_size: Players per batch (defaults to config.batch_size)
            country_code: Optional country code to associate with players

        Returns:
            Absolute path to database file

        Raises:
            ValueError: If players list is empty
            sqlite3.Error: If database operations fail
        """
        if not players:
            raise ValueError("Cannot export empty player list")

        batch_size = batch_size or self.config.batch_size
        db_path = Path(db_path)

        start_time = time.time()
        timestamp = datetime.now().isoformat()

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Create table and indexes
            cursor.executescript(self.SQLITE_SCHEMA)

            # Prepare insert statement
            insert_sql = """
            INSERT INTO youth_players (
                first_name, last_name, full_name, nationality, age,
                position, current_ability, potential_ability,
                height, weight, preferred_foot, birth_date,
                pace, acceleration, stamina, strength,
                shooting, passing, dribbling, crossing, first_touch,
                tackling, marking, positioning, vision, decisions,
                reflexes, handling, kicking, one_on_one,
                work_rate, determination, leadership, teamwork, aggression,
                finishing, long_shots, heading, free_kicks, penalty_taking,
                corners, throw_ins, technique, flair, composure,
                export_timestamp, country_code
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
            )
            """

            # Bulk insert in batches
            for batch in self._batched(players, batch_size):
                batch_data = []
                for player in batch:
                    player_dict = self._player_to_dict(player)

                    # Helper to safely get value from dict or attributes
                    def get_val(key: str, default=None):
                        if key in player_dict:
                            return player_dict[key]
                        if player.attributes and key in player.attributes:
                            return player.attributes[key]
                        return default

                    row = (
                        player.first_name,
                        player.last_name,
                        player.full_name,
                        player.nationality,
                        player.age,
                        player.position.value
                        if hasattr(player.position, "value")
                        else str(player.position),
                        player.current_ability,
                        player.potential_ability,
                        player.height,
                        player.weight,
                        player.preferred_foot.value
                        if hasattr(player.preferred_foot, "value")
                        else str(player.preferred_foot),
                        player.birth_date.isoformat(),
                        get_val("pace"),
                        get_val("acceleration"),
                        get_val("stamina"),
                        get_val("strength"),
                        get_val("shooting"),
                        get_val("passing"),
                        get_val("dribbling"),
                        get_val("crossing"),
                        get_val("first_touch"),
                        get_val("tackling"),
                        get_val("marking"),
                        get_val("positioning"),
                        get_val("vision"),
                        get_val("decisions"),
                        get_val("reflexes"),
                        get_val("handling"),
                        get_val("kicking"),
                        get_val("one_on_one"),
                        get_val("work_rate"),
                        get_val("determination"),
                        get_val("leadership"),
                        get_val("teamwork"),
                        get_val("aggression"),
                        get_val("finishing"),
                        get_val("long_shots"),
                        get_val("heading"),
                        get_val("free_kicks"),
                        get_val("penalty_taking"),
                        get_val("corners"),
                        get_val("throw_ins"),
                        get_val("technique"),
                        get_val("flair"),
                        get_val("composure"),
                        timestamp,
                        country_code,
                    )
                    batch_data.append(row)

                cursor.executemany(insert_sql, batch_data)
                conn.commit()

            conn.close()

        except sqlite3.Error as e:
            if db_path.exists():
                db_path.unlink()
            raise sqlite3.Error(f"Failed to export to SQLite: {e}")

        elapsed = time.time() - start_time
        print(f"Exported {len(players)} players to SQLite in {elapsed:.2f}s")

        return str(db_path.absolute())

    def export_all(
        self,
        players_by_country: Dict[str, List[YouthPlayer]],
        formats: Optional[List[str]] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """Export players for all countries to specified formats.

        Exports players for each country to all requested formats. Each export
        is done sequentially to avoid memory issues. Returns a dictionary mapping
        each format to a list of exported file paths.

        Args:
            players_by_country: Dictionary mapping country codes to player lists
            formats: List of formats to export ('json', 'csv', 'sqlite').
                    Defaults to all formats in config.
            timestamp: Optional timestamp for filenames

        Returns:
            Dictionary mapping format names to lists of file paths
            e.g., {'json': ['/path/ENG_20240115_103000.json', ...], ...}
        """
        if formats is None:
            formats = [f.value for f in self.config.formats]

        formats = [f.lower() for f in formats]
        results: Dict[str, List[str]] = {fmt: [] for fmt in formats}

        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        total_countries = len(players_by_country)
        print(f"Exporting {total_countries} countries to formats: {formats}")

        for idx, (country_code, players) in enumerate(players_by_country.items(), 1):
            print(f"[{idx}/{total_countries}] Exporting {country_code}: {len(players)} players")

            if "json" in formats:
                filepath = self._get_filepath(country_code, "json", timestamp)
                exported = self.export_to_json(players, str(filepath))
                results["json"].append(exported)

            if "csv" in formats:
                filepath = self._get_filepath(country_code, "csv", timestamp)
                exported = self.export_to_csv(players, str(filepath))
                results["csv"].append(exported)

            if "sqlite" in formats:
                # SQLite files per country
                filepath = self._get_filepath(country_code, "db", timestamp)
                exported = self.export_to_sqlite(players, str(filepath), country_code=country_code)
                results["sqlite"].append(exported)

        return results

    def export_to_single_sqlite(
        self,
        players_by_country: Dict[str, List[YouthPlayer]],
        db_path: Optional[str] = None,
        batch_size: Optional[int] = None,
    ) -> str:
        """Export all countries to a single SQLite database.

        Creates one database with all players, adding a country_code column
        to distinguish between countries.

        Args:
            players_by_country: Dictionary mapping country codes to player lists
            db_path: Optional path for database (defaults to output_dir/all_countries_TIMESTAMP.db)
            batch_size: Players per batch

        Returns:
            Absolute path to database file
        """
        if db_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_path = self.output_dir / f"all_countries_{timestamp}.db"

        db_path = Path(db_path)
        batch_size = batch_size or self.config.batch_size
        timestamp = datetime.now().isoformat()

        start_time = time.time()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.executescript(self.SQLITE_SCHEMA)

        insert_sql = """
        INSERT INTO youth_players (
            first_name, last_name, full_name, nationality, age,
            position, current_ability, potential_ability,
            height, weight, preferred_foot, birth_date,
            pace, acceleration, stamina, strength,
            shooting, passing, dribbling, crossing, first_touch,
            tackling, marking, positioning, vision, decisions,
            reflexes, handling, kicking, one_on_one,
            work_rate, determination, leadership, teamwork, aggression,
            finishing, long_shots, heading, free_kicks, penalty_taking,
            corners, throw_ins, technique, flair, composure,
            export_timestamp, country_code
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?
        )
        """

        total_players = 0
        for country_code, players in players_by_country.items():
            print(f"Exporting {country_code}: {len(players)} players to combined DB")

            for batch in self._batched(players, batch_size):
                batch_data = []
                for player in batch:
                    player_dict = self._player_to_dict(player)

                    def get_val(key: str, default=None):
                        if key in player_dict:
                            return player_dict[key]
                        if player.attributes and key in player.attributes:
                            return player.attributes[key]
                        return default

                    row = (
                        player.first_name,
                        player.last_name,
                        player.full_name,
                        player.nationality,
                        player.age,
                        str(
                            player.position.value
                            if hasattr(player.position, "value")
                            else player.position
                        ),
                        player.current_ability,
                        player.potential_ability,
                        player.height,
                        player.weight,
                        str(
                            player.preferred_foot.value
                            if hasattr(player.preferred_foot, "value")
                            else player.preferred_foot
                        ),
                        player.birth_date.isoformat(),
                        get_val("pace"),
                        get_val("acceleration"),
                        get_val("stamina"),
                        get_val("strength"),
                        get_val("shooting"),
                        get_val("passing"),
                        get_val("dribbling"),
                        get_val("crossing"),
                        get_val("first_touch"),
                        get_val("tackling"),
                        get_val("marking"),
                        get_val("positioning"),
                        get_val("vision"),
                        get_val("decisions"),
                        get_val("reflexes"),
                        get_val("handling"),
                        get_val("kicking"),
                        get_val("one_on_one"),
                        get_val("work_rate"),
                        get_val("determination"),
                        get_val("leadership"),
                        get_val("teamwork"),
                        get_val("aggression"),
                        get_val("finishing"),
                        get_val("long_shots"),
                        get_val("heading"),
                        get_val("free_kicks"),
                        get_val("penalty_taking"),
                        get_val("corners"),
                        get_val("throw_ins"),
                        get_val("technique"),
                        get_val("flair"),
                        get_val("composure"),
                        timestamp,
                        country_code,
                    )
                    batch_data.append(row)

                cursor.executemany(insert_sql, batch_data)
                conn.commit()

            total_players += len(players)

        conn.close()

        elapsed = time.time() - start_time
        print(
            f"Exported {total_players} players from {len(players_by_country)} countries to SQLite in {elapsed:.2f}s"
        )

        return str(db_path.absolute())


# Convenience functions for quick exports
def export_players_to_json(
    players: List[YouthPlayer], output_dir: str = "data/youth_players/", batch_size: int = 10000
) -> str:
    """Quick export players to JSON with default settings.

    Args:
        players: List of YouthPlayer objects
        output_dir: Output directory path
        batch_size: Players per batch

    Returns:
        Path to exported file
    """
    config = ExportConfig(
        formats=[], batch_size=batch_size, output_dir=output_dir, compression=False
    )
    exporter = YouthPlayerExporter(config)
    filepath = exporter._get_filepath("export", "json")
    return exporter.export_to_json(players, str(filepath))


def export_players_to_csv(
    players: List[YouthPlayer], output_dir: str = "data/youth_players/", batch_size: int = 10000
) -> str:
    """Quick export players to CSV with default settings.

    Args:
        players: List of YouthPlayer objects
        output_dir: Output directory path
        batch_size: Players per batch

    Returns:
        Path to exported file
    """
    config = ExportConfig(
        formats=[], batch_size=batch_size, output_dir=output_dir, compression=False
    )
    exporter = YouthPlayerExporter(config)
    filepath = exporter._get_filepath("export", "csv")
    return exporter.export_to_csv(players, str(filepath))


def export_players_to_sqlite(
    players: List[YouthPlayer], output_dir: str = "data/youth_players/", batch_size: int = 10000
) -> str:
    """Quick export players to SQLite with default settings.

    Args:
        players: List of YouthPlayer objects
        output_dir: Output directory directory path
        batch_size: Players per batch

    Returns:
        Path to exported file
    """
    config = ExportConfig(
        formats=[], batch_size=batch_size, output_dir=output_dir, compression=False
    )
    exporter = YouthPlayerExporter(config)
    filepath = exporter._get_filepath("export", "db")
    return exporter.export_to_sqlite(players, str(filepath))
