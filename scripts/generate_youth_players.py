#!/usr/bin/env python3
"""CLI script for generating youth players for FM Manager.

This script provides a command-line interface for the youth player generation
system, supporting generation, filtering, and export to multiple formats.

Usage Examples:
    # Generate all countries
    python scripts/generate_youth_players.py

    # Generate specific countries
    python scripts/generate_youth_players.py --countries ENG ESP GER

    # Export to multiple formats
    python scripts/generate_youth_players.py --formats json csv sqlite

    # Custom output directory
    python scripts/generate_youth_players.py --output-dir /tmp/youth_players/

    # Generate without filtering (for testing)
    python scripts/generate_youth_players.py --no-filter --countries CHN
"""

import argparse
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("Warning: tqdm not installed. Progress bars will not be shown.")
    print("Install with: pip install tqdm")

from fm_manager.config.youth_generation_config import (
    YouthGenerationConfig,
    ExportConfig,
    ExportFormat,
)
from fm_manager.engine.youth_orchestrator import (
    YouthGenerationOrchestrator,
    GenerationResult,
    ExportResult,
)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI.

    Args:
        verbose: If True, set DEBUG level; otherwise INFO
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def check_disk_space(path: Path, required_gb: float = 1.0) -> bool:
    """Check if there's sufficient disk space at the given path.

    Args:
        path: Path to check
        required_gb: Minimum required space in GB

    Returns:
        True if sufficient space available
    """
    try:
        stat = shutil.disk_usage(path)
        available_gb = stat.free / (1024**3)
        return available_gb >= required_gb
    except Exception:
        # If we can't check, assume it's OK
        return True


def validate_output_dir(output_dir: Path) -> None:
    """Validate that output directory exists and is writable.

    Args:
        output_dir: Directory path to validate

    Raises:
        SystemExit: If directory is invalid or not writable
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        # Test write permission
        test_file = output_dir / ".write_test"
        test_file.touch()
        test_file.unlink()

    except PermissionError:
        print(f"Error: No write permission to directory: {output_dir}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Cannot create or access directory {output_dir}: {e}")
        sys.exit(1)


def validate_country_codes(country_codes: List[str], config: YouthGenerationConfig) -> List[str]:
    """Validate country codes against configuration.

    Args:
        country_codes: List of country codes to validate
        config: Youth generation configuration

    Returns:
        Validated list of country codes

    Raises:
        SystemExit: If any country code is invalid
    """
    available = sorted(config.countries.keys())
    invalid = [code for code in country_codes if code not in config.countries]

    if invalid:
        print(f"Error: Invalid country code(s): {', '.join(invalid)}")
        print(f"\nAvailable country codes:")
        # Print in columns
        cols = 5
        for i in range(0, len(available), cols):
            row = available[i : i + cols]
            print("  " + "  ".join(f"{code:<6}" for code in row))
        sys.exit(1)

    return country_codes


class ProgressTracker:
    """Track and display progress for generation operations."""

    def __init__(self, total_countries: int, use_tqdm: bool = True):
        """Initialize progress tracker.

        Args:
            total_countries: Total number of countries to process
            use_tqdm: Whether to use tqdm progress bars
        """
        self.total_countries = total_countries
        self.use_tqdm = use_tqdm and HAS_TQDM
        self.current_country: Optional[str] = None
        self.generation_bar = None
        self.filtering_bar = None
        self.overall_bar = None

    def __enter__(self):
        """Context manager entry."""
        if self.use_tqdm:
            self.overall_bar = tqdm(
                total=self.total_countries,
                desc="Overall Progress",
                position=0,
                leave=True,
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} countries",
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close all progress bars."""
        if self.generation_bar:
            self.generation_bar.close()
        if self.filtering_bar:
            self.filtering_bar.close()
        if self.overall_bar:
            self.overall_bar.close()

    def start_country(self, country_code: str, pool_size: int):
        """Start tracking progress for a new country.

        Args:
            country_code: Country being processed
            pool_size: Total pool size for generation
        """
        self.current_country = country_code

        if self.use_tqdm:
            # Close previous bars
            if self.generation_bar:
                self.generation_bar.close()
            if self.filtering_bar:
                self.filtering_bar.close()

            # Create new generation bar
            self.generation_bar = tqdm(
                total=pool_size,
                desc=f"Generating {country_code}",
                position=1,
                leave=False,
                unit=" players",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )

    def update_generation(self, current: int, total: int):
        """Update generation progress.

        Args:
            current: Current progress
            total: Total to generate
        """
        if self.use_tqdm and self.generation_bar:
            self.generation_bar.n = current
            self.generation_bar.total = total
            self.generation_bar.refresh()
        elif not self.use_tqdm and current % max(1, total // 10) == 0:
            # Simple console progress without tqdm
            pct = (current / total) * 100
            print(f"  {self.current_country} Generation: {pct:.0f}% ({current:,}/{total:,})")

    def start_filtering(self, total: int):
        """Start tracking filtering progress.

        Args:
            total: Total players to filter
        """
        if self.use_tqdm:
            if self.generation_bar:
                self.generation_bar.close()

            self.filtering_bar = tqdm(
                total=total,
                desc=f"Filtering {self.current_country}",
                position=1,
                leave=False,
                unit=" players",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )

    def update_filtering(self, current: int, total: int):
        """Update filtering progress.

        Args:
            current: Current progress
            total: Total to filter
        """
        if self.use_tqdm and self.filtering_bar:
            self.filtering_bar.n = current
            self.filtering_bar.total = total
            self.filtering_bar.refresh()

    def complete_country(self):
        """Mark current country as complete."""
        if self.use_tqdm:
            if self.generation_bar:
                self.generation_bar.close()
                self.generation_bar = None
            if self.filtering_bar:
                self.filtering_bar.close()
                self.filtering_bar = None
            if self.overall_bar:
                self.overall_bar.update(1)


def print_statistics(results: Dict[str, GenerationResult], export_result: ExportResult):
    """Print formatted statistics report.

    Args:
        results: Dictionary of generation results by country
        export_result: Export operation results
    """
    print("\n" + "=" * 70)
    print("YOUTH GENERATION STATISTICS REPORT")
    print("=" * 70)

    # Summary statistics
    total_generated = sum(r.players_generated for r in results.values())
    total_filtered = sum(r.players_filtered for r in results.values())
    total_time = sum(r.generation_time + r.filtering_time for r in results.values())

    print(f"\nOverall Summary:")
    print(f"  Countries processed: {len(results)}")
    print(f"  Total players generated: {total_generated:,}")
    print(f"  Total players retained: {total_filtered:,}")
    print(f"  Retention rate: {(total_filtered / total_generated * 100):.2f}%")
    print(f"  Total generation time: {total_time:.2f}s")
    print(f"  Export time: {export_result.export_time:.2f}s")
    print(f"  Total time: {total_time + export_result.export_time:.2f}s")

    # Per-country breakdown
    print(f"\nPer-Country Breakdown:")
    print(
        f"  {'Country':<8} {'Generated':>12} {'Retained':>12} {'Rate':>8} {'Gen Time':>10} {'Filter Time':>12}"
    )
    print("  " + "-" * 68)

    for code in sorted(results.keys()):
        r = results[code]
        rate = (r.players_filtered / r.players_generated * 100) if r.players_generated > 0 else 0
        print(
            f"  {code:<8} "
            f"{r.players_generated:>12,} "
            f"{r.players_filtered:>12,} "
            f"{rate:>7.1f}% "
            f"{r.generation_time:>9.2f}s "
            f"{r.filtering_time:>11.2f}s"
        )

        if r.errors:
            for error in r.errors:
                print(f"    ERROR: {error}")

    # Export details
    print(f"\nExported Files:")
    for fmt, paths in export_result.export_paths.items():
        print(f"  {fmt.upper()}:")
        for path in paths:
            file_size = Path(path).stat().st_size / (1024**2)  # MB
            print(f"    - {path} ({file_size:.2f} MB)")

    print("\n" + "=" * 70)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate youth players for FM Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all countries
  python scripts/generate_youth_players.py
  
  # Generate specific countries
  python scripts/generate_youth_players.py --countries ENG ESP GER
  
  # Export to multiple formats
  python scripts/generate_youth_players.py --formats json csv sqlite
  
  # Custom output directory
  python scripts/generate_youth_players.py --output-dir /tmp/youth_players/
  
  # Generate without filtering (for testing)
  python scripts/generate_youth_players.py --no-filter --countries CHN
  
  # Quiet mode (no progress bars)
  python scripts/generate_youth_players.py --quiet --countries ENG
        """,
    )

    parser.add_argument(
        "--config",
        default="fm_manager/config/youth_generation.yaml",
        help="Path to YAML configuration file (default: fm_manager/config/youth_generation.yaml)",
    )

    parser.add_argument(
        "--countries",
        nargs="+",
        help="Country codes to generate (default: all configured countries)",
    )

    parser.add_argument("--output-dir", help="Output directory override (default: from config)")

    parser.add_argument(
        "--formats",
        nargs="+",
        default=["json"],
        choices=["json", "csv", "sqlite"],
        help="Export formats (default: json)",
    )

    parser.add_argument(
        "--no-filter", action="store_true", help="Skip filtering phase (generate all players)"
    )

    parser.add_argument(
        "--parallel", action="store_true", help="Generate countries in parallel (experimental)"
    )

    parser.add_argument(
        "--quiet", action="store_true", help="Suppress progress bars and non-essential output"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose (DEBUG) logging")

    parser.add_argument(
        "--dry-run", action="store_true", help="Validate configuration without generating players"
    )

    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    args = parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    # Load configuration
    try:
        config_path = Path(args.config)
        if not config_path.is_absolute():
            config_path = Path(__file__).parent.parent / config_path

        logger.info(f"Loading configuration from {config_path}")
        config = YouthGenerationConfig.load(str(config_path))

    except FileNotFoundError as e:
        print(f"Error: Configuration file not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Validate and prepare country codes
    if args.countries:
        country_codes = validate_country_codes(args.countries, config)
    else:
        country_codes = sorted(config.countries.keys())

    print(f"Youth Generation Configuration:")
    print(f"  Config file: {config_path}")
    print(
        f"  Countries: {len(country_codes)} ({', '.join(country_codes[:5])}{'...' if len(country_codes) > 5 else ''})"
    )
    print(f"  Formats: {', '.join(args.formats)}")
    print(f"  Filtering: {'disabled' if args.no_filter else 'enabled'}")

    # Dry run mode
    if args.dry_run:
        print("\nDry run mode - validating configuration...")
        errors = config.validate()
        if errors:
            print("Configuration errors found:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("Configuration is valid.")
            sys.exit(0)

    # Setup output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        config.export.output_dir = str(output_dir)
    else:
        output_dir = Path(config.export.output_dir)

    validate_output_dir(output_dir)

    # Check disk space (estimate 1GB per country for safety)
    required_gb = len(country_codes) * 1.0
    if not check_disk_space(output_dir, required_gb):
        print(f"Error: Insufficient disk space. At least {required_gb:.1f} GB required.")
        sys.exit(1)

    print(f"  Output directory: {output_dir.absolute()}")
    print()

    # Initialize orchestrator
    logger.info("Initializing YouthGenerationOrchestrator")
    orchestrator = YouthGenerationOrchestrator(config)

    # Track results
    results: Dict[str, GenerationResult] = {}
    start_time = time.time()

    # Process countries with progress tracking
    with ProgressTracker(len(country_codes), use_tqdm=not args.quiet) as tracker:
        for idx, country_code in enumerate(country_codes, 1):
            if not args.quiet:
                print(f"[{idx}/{len(country_codes)}] Processing {country_code}...")

            country_config = config.countries[country_code]
            tracker.start_country(country_code, country_config.pool_size)

            def progress_callback(phase: str, current: int, total: int):
                if phase == "generation":
                    tracker.update_generation(current, total)
                elif phase == "filtering":
                    if current == 0:  # First call
                        tracker.start_filtering(total)
                    tracker.update_filtering(current, total)

            try:
                result = orchestrator.generate_for_country(
                    country_code=country_code,
                    skip_filtering=args.no_filter,
                    progress_callback=progress_callback if not args.quiet else None,
                )
                results[country_code] = result

                if not args.quiet:
                    if result.success:
                        print(
                            f"  Generated {result.players_generated:,} players, "
                            f"retained {result.players_filtered:,} "
                            f"({result.retention_rate * 100:.1f}%)"
                        )
                    else:
                        print(f"  Errors: {', '.join(result.errors)}")

            except Exception as e:
                logger.error(f"Failed to process {country_code}: {e}", exc_info=True)
                print(f"  ERROR: {e}")
                # Create error result
                results[country_code] = GenerationResult(country_code=country_code, errors=[str(e)])

            tracker.complete_country()

    # Export phase
    if not args.quiet:
        print("\nExporting players...")

    export_start = time.time()

    try:
        # Build players_by_country from results
        players_by_country = {}
        for country_code, result in results.items():
            if result.success and result.players_filtered > 0:
                # Regenerate with filtering to get actual player objects
                if args.no_filter:
                    players = orchestrator.batch_generator.generate_for_country(country_code)
                else:
                    # Generate and filter separately
                    from fm_manager.engine.youth_filtering import YouthPlayer as FilterYouthPlayer

                    # Generate all players
                    all_players = orchestrator.batch_generator.generate_for_country(country_code)

                    # Convert to filtering format
                    filter_players = []
                    for i, p in enumerate(all_players):
                        fp = FilterYouthPlayer(
                            id=i,
                            full_name=p.full_name,
                            nationality=p.nationality,
                            age=p.age,
                            position=p.position.value
                            if hasattr(p.position, "value")
                            else str(p.position),
                            ca=float(p.current_ability),
                            pa=float(p.potential_ability),
                            attributes=p.attributes,
                        )
                        filter_players.append(fp)

                    # Apply filtering
                    filter_result = orchestrator.filtering_pipeline.filter_players(
                        filter_players, by_country=False
                    )
                    selected_ids = {p.id for p in filter_result.selected_players}

                    # Return filtered players
                    players = [all_players[i] for i in selected_ids if i < len(all_players)]

                players_by_country[country_code] = players

        # Export
        export_result = orchestrator.export_existing(
            players_by_country=players_by_country,
            formats=args.formats,
        )

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        print(f"Export error: {e}")
        export_result = ExportResult(country_results=results, export_paths={}, errors=[str(e)])

    # Print final statistics
    if not args.quiet:
        print_statistics(results, export_result)

    # Summary
    total_time = time.time() - start_time
    total_players = sum(r.players_filtered for r in results.values())
    success_count = sum(1 for r in results.values() if r.success)

    print(
        f"\nCompleted: {success_count}/{len(country_codes)} countries, "
        f"{total_players:,} players exported in {total_time:.2f}s"
    )

    # Exit with error code if any country failed
    if any(not r.success for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
