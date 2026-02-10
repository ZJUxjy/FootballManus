"""Youth Generation Orchestration Layer.

This module provides the main orchestration layer for the youth player generation system,
tying together batch generation, filtering, and export components into a unified pipeline.

Example:
    >>> from fm_manager.engine.youth_orchestrator import YouthGenerationOrchestrator
    >>> from fm_manager.config.youth_generation_config import YouthGenerationConfig
    >>>
    >>> config = YouthGenerationConfig.load()
    >>> orchestrator = YouthGenerationOrchestrator(config)
    >>>
    >>> # Generate for one country
    >>> result = orchestrator.generate_for_country("ENG")
    >>>
    >>> # Generate for all countries
    >>> results = orchestrator.generate_all_countries()
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from fm_manager.config.youth_generation_config import (
    FilteringConfig,
    YouthGenerationConfig,
)
from fm_manager.engine.youth_batch_generator import (
    YouthBatchGenerator,
    YouthPlayer,
)
from fm_manager.engine.youth_filtering import (
    FilteringResult as FilteringStats,
    YouthFilteringPipeline,
    FilteringConfig as CoreFilteringConfig,
)
from fm_manager.engine.youth_exporter import YouthPlayerExporter


class FilteringPipelineAdapter:
    """Adapter to make the core filtering pipeline work with batch generator interface.

    The batch generator expects a filter_batch() method that operates on YouthPlayer
    objects from the batch generator. The core filtering pipeline has filter_players()
    which expects different YouthPlayer objects and returns a FilteringResult.
    """

    def __init__(self, config: CoreFilteringConfig):
        """Initialize adapter with filtering configuration.

        Args:
            config: Filtering configuration
        """
        self.core_pipeline = YouthFilteringPipeline(config)
        self.min_ca = 0  # Filtering happens in core pipeline
        self.min_pa = 0
        self.max_age = 100

    def filter_batch(self, players: List[YouthPlayer]) -> List[YouthPlayer]:
        """Filter a batch of players using the core filtering pipeline.

        Args:
            players: List of YouthPlayer objects from batch generator

        Returns:
            Filtered list of YouthPlayer objects
        """
        # Convert to filtering module's format
        from fm_manager.engine.youth_filtering import YouthPlayer as FilterYouthPlayer

        filter_players = []
        for i, p in enumerate(players):
            filter_player = FilterYouthPlayer(
                id=i,
                full_name=p.full_name,
                nationality=p.nationality,
                age=p.age,
                position=p.position.value if hasattr(p.position, "value") else str(p.position),
                ca=float(p.current_ability),
                pa=float(p.potential_ability),
                attributes=p.attributes,
            )
            filter_players.append(filter_player)

        # Apply filtering
        result = self.core_pipeline.filter_players(filter_players, by_country=False)

        # Get indices of selected players
        selected_ids = {p.id for p in result.selected_players}

        # Return original players that were selected
        return [players[i] for i in selected_ids if i < len(players)]


logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Results from a generation operation for a single country.

    Attributes:
        country_code: ISO country code
        players_generated: Number of players initially generated
        players_filtered: Number of players retained after filtering
        filtering_result: Detailed filtering statistics
        generation_time: Time taken for generation phase
        filtering_time: Time taken for filtering phase
        errors: List of any errors encountered
    """

    country_code: str
    players_generated: int = 0
    players_filtered: int = 0
    filtering_result: Optional[FilteringStats] = None
    generation_time: float = 0.0
    filtering_time: float = 0.0
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if generation completed without errors."""
        return len(self.errors) == 0

    @property
    def retention_rate(self) -> float:
        """Calculate player retention rate after filtering."""
        if self.players_generated == 0:
            return 0.0
        return self.players_filtered / self.players_generated


@dataclass
class ExportResult:
    """Results from an export operation.

    Attributes:
        country_results: Dictionary mapping country codes to generation results
        export_paths: Dictionary mapping formats to lists of file paths
        export_time: Time taken for export phase
        total_players_exported: Total number of players exported
        errors: List of any errors encountered
    """

    country_results: Dict[str, GenerationResult]
    export_paths: Dict[str, List[str]]
    export_time: float = 0.0
    total_players_exported: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if export completed without errors."""
        return len(self.errors) == 0

    def get_summary(self) -> Dict:
        """Get a summary of the export operation."""
        total_generated = sum(r.players_generated for r in self.country_results.values())
        total_filtered = sum(r.players_filtered for r in self.country_results.values())
        total_time = sum(
            r.generation_time + r.filtering_time for r in self.country_results.values()
        )

        return {
            "countries_processed": len(self.country_results),
            "total_players_generated": total_generated,
            "total_players_filtered": total_filtered,
            "total_players_exported": self.total_players_exported,
            "retention_rate": total_filtered / total_generated if total_generated > 0 else 0.0,
            "generation_time_seconds": total_time,
            "export_time_seconds": self.export_time,
            "total_time_seconds": total_time + self.export_time,
            "export_paths": self.export_paths,
            "errors": self.errors,
        }


class YouthGenerationOrchestrator:
    """Main orchestrator for youth player generation pipeline.

    This class ties together all components of the youth generation system:
    - YouthBatchGenerator: Generates youth players in batches
    - YouthFilteringPipeline: Filters players based on CA/PA criteria
    - YouthPlayerExporter: Exports filtered players to various formats

    Usage:
        >>> config = YouthGenerationConfig.load()
        >>> orchestrator = YouthGenerationOrchestrator(config)
        >>>
        >>> # Generate, filter, and export for one country
        >>> result = orchestrator.generate_for_country("ENG")
        >>>
        >>> # Or do it all in one step
        >>> export_result = orchestrator.generate_and_export(["ENG", "ESP"])
    """

    def __init__(self, config: YouthGenerationConfig):
        """Initialize the orchestrator with configuration.

        Args:
            config: Youth generation configuration including country settings,
                   filtering parameters, and export settings.
        """
        self.config = config
        self.batch_generator = YouthBatchGenerator(config)
        # Use adapter to bridge between config's FilteringConfig and filtering module's expected config
        # Create filtering config for the pipeline from the config's filtering settings
        filter_config = CoreFilteringConfig(
            ca_percentile=config.filtering.ca_percentile,
            pa_percentile=config.filtering.pa_percentile,
            min_players_per_country=config.filtering.min_players_per_country,
            ca_pa_ratio_min=config.filtering.ca_pa_ratio_min,
        )
        self.filtering_pipeline = YouthFilteringPipeline(filter_config)
        self.exporter = YouthPlayerExporter(config.export)

        logger.info(
            f"Initialized YouthGenerationOrchestrator with "
            f"{len(config.countries)} countries, "
            f"filtering config: CA={config.filtering.ca_percentile}, "
            f"PA={config.filtering.pa_percentile}"
        )

    def _validate_country_code(self, country_code: str) -> None:
        """Validate that a country code exists in the configuration.

        Args:
            country_code: ISO country code to validate

        Raises:
            ValueError: If country code is not found in configuration
        """
        if country_code not in self.config.countries:
            available = sorted(self.config.countries.keys())
            raise ValueError(
                f"Invalid country code '{country_code}'. "
                f"Available countries: {', '.join(available)}"
            )

    def generate_for_country(
        self,
        country_code: str,
        skip_filtering: bool = False,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> GenerationResult:
        """Generate and optionally filter youth players for one country.

        This is the main method for processing a single country. It generates
        the full youth pool, applies filtering criteria, and returns detailed
        statistics.

        Args:
            country_code: ISO country code (e.g., 'ENG', 'ESP')
            skip_filtering: If True, skip the filtering phase
            progress_callback: Optional callback(current, total, phase) for progress updates

        Returns:
            GenerationResult with statistics and any filtered players

        Raises:
            ValueError: If country_code is not found in configuration

        Example:
            >>> result = orchestrator.generate_for_country("ENG")
            >>> print(f"Generated {result.players_generated}, kept {result.players_filtered}")
        """
        self._validate_country_code(country_code)

        result = GenerationResult(country_code=country_code)
        country_config = self.config.countries[country_code]

        logger.info(f"Starting generation for {country_code} ({country_config.name})")

        try:
            # Phase 1: Generation
            logger.debug(
                f"Phase 1: Generating {country_config.pool_size} players for {country_code}"
            )

            def _gen_progress(current: int, total: int) -> None:
                if progress_callback:
                    progress_callback("generation", current, total)

            gen_start = time.time()
            players = self.batch_generator.generate_for_country(
                country_code=country_code,
                progress_callback=_gen_progress if progress_callback else None,
            )
            result.generation_time = time.time() - gen_start
            result.players_generated = len(players)

            logger.info(
                f"Generated {len(players)} players for {country_code} "
                f"in {result.generation_time:.2f}s"
            )

            # Phase 2: Filtering (optional)
            if skip_filtering:
                logger.debug(f"Skipping filtering for {country_code}")
                result.players_filtered = len(players)
            else:
                logger.debug(f"Phase 2: Filtering players for {country_code}")

                def _filter_progress(current: int, total: int) -> None:
                    if progress_callback:
                        progress_callback("filtering", current, total)

                filter_start = time.time()

                # Convert YouthPlayer to filtering module's YouthPlayer format
                # The filtering module expects a different YouthPlayer dataclass
                from fm_manager.engine.youth_filtering import YouthPlayer as FilterYouthPlayer

                filter_players = []
                for i, p in enumerate(players):
                    filter_player = FilterYouthPlayer(
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
                    filter_players.append(filter_player)

                filtering_result = self.filtering_pipeline.filter_players(
                    filter_players,
                    by_country=False,  # Already filtering per country
                )

                result.filtering_time = time.time() - filter_start
                result.filtering_result = filtering_result
                result.players_filtered = len(filtering_result.selected_players)

                logger.info(
                    f"Filtered {country_code}: {result.players_filtered}/{result.players_generated} "
                    f"retained ({result.retention_rate * 100:.2f}%) in {result.filtering_time:.2f}s"
                )

                if progress_callback:
                    progress_callback(
                        "filtering", result.players_filtered, result.players_generated
                    )

        except Exception as e:
            error_msg = f"Error processing {country_code}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)

        return result

    def generate_all_countries(
        self,
        skip_filtering: bool = False,
        parallel: bool = False,
        progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
    ) -> Dict[str, GenerationResult]:
        """Generate youth players for all configured countries.

        Processes each country sequentially by default, but can be run in parallel
        for faster processing (at the cost of higher memory usage).

        Args:
            skip_filtering: If True, skip the filtering phase
            parallel: If True, process countries in parallel (experimental)
            progress_callback: Optional callback(country, phase, current, total) for updates

        Returns:
            Dictionary mapping country codes to GenerationResult objects

        Example:
            >>> results = orchestrator.generate_all_countries()
            >>> for code, result in results.items():
            ...     print(f"{code}: {result.players_filtered} players")
        """
        results = {}
        country_codes = sorted(self.config.countries.keys())
        total_countries = len(country_codes)

        logger.info(f"Starting generation for {total_countries} countries")

        for idx, country_code in enumerate(country_codes, 1):
            logger.info(f"[{idx}/{total_countries}] Processing {country_code}")

            def _country_progress(phase: str, current: int, total: int) -> None:
                if progress_callback:
                    progress_callback(country_code, phase, current, total)

            result = self.generate_for_country(
                country_code=country_code,
                skip_filtering=skip_filtering,
                progress_callback=_country_progress if progress_callback else None,
            )
            results[country_code] = result

            if progress_callback:
                progress_callback(country_code, "complete", idx, total_countries)

        # Log summary
        total_generated = sum(r.players_generated for r in results.values())
        total_filtered = sum(r.players_filtered for r in results.values() if r.filtering_result)
        total_errors = sum(len(r.errors) for r in results.values())

        logger.info(
            f"Completed generation for {total_countries} countries: "
            f"{total_generated} generated, {total_filtered} retained, "
            f"{total_errors} errors"
        )

        return results

    def generate_and_export(
        self,
        country_codes: Optional[List[str]] = None,
        formats: Optional[List[str]] = None,
        skip_filtering: bool = False,
        progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
    ) -> ExportResult:
        """Generate, filter, and export youth players in one operation.

        This is the complete pipeline method that handles generation, filtering,
        and export to all requested formats.

        Args:
            country_codes: List of country codes to process (default: all configured)
            formats: List of export formats (default: from config)
            skip_filtering: If True, skip the filtering phase
            progress_callback: Optional callback(country, phase, current, total) for updates

        Returns:
            ExportResult with all generation statistics and export paths

        Example:
            >>> result = orchestrator.generate_and_export(
            ...     country_codes=["ENG", "ESP"],
            ...     formats=["json", "csv"]
            ... )
            >>> print(result.get_summary())
        """
        # Validate and normalize country codes
        if country_codes is None:
            country_codes = sorted(self.config.countries.keys())
        else:
            for code in country_codes:
                self._validate_country_code(code)

        # Normalize formats
        if formats is None:
            formats = [f.value for f in self.config.export.formats]
        formats = [f.lower() for f in formats]

        logger.info(
            f"Starting generate_and_export for {len(country_codes)} countries to formats: {formats}"
        )

        # Phase 1 & 2: Generate and filter
        country_results = {}
        players_by_country: Dict[str, List[YouthPlayer]] = {}

        for idx, country_code in enumerate(country_codes, 1):
            logger.info(f"[{idx}/{len(country_codes)}] Processing {country_code}")

            def _progress(phase: str, current: int, total: int) -> None:
                if progress_callback:
                    progress_callback(country_code, phase, current, total)

            result = self.generate_for_country(
                country_code=country_code,
                skip_filtering=skip_filtering,
                progress_callback=_progress if progress_callback else None,
            )
            country_results[country_code] = result

            # Convert filtered players back to batch generator format for export
            if result.filtering_result and result.filtering_result.selected_players:
                # Need to convert back from filtering module's YouthPlayer to batch generator's
                # Since they have different fields, we'll need to regenerate or store original
                # For now, we'll store the original players if not filtering, or regenerate filtered
                if skip_filtering:
                    # Regenerate to get the full player objects
                    players = self.batch_generator.generate_for_country(country_code)
                    players_by_country[country_code] = players
                else:
                    # We need to convert filtered players back
                    # Since the filtering module's YouthPlayer doesn't have all fields,
                    # we'll filter from the original generation
                    logger.debug(f"Regenerating {country_code}")
                    players = self.batch_generator.generate_for_country(country_code)
                    # Convert to filtering format and filter
                    from fm_manager.engine.youth_filtering import YouthPlayer as FilterYouthPlayer

                    filter_players = []
                    for i, p in enumerate(players):
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
                    filter_result = self.filtering_pipeline.filter_players(
                        filter_players, by_country=False
                    )
                    selected_ids = {p.id for p in filter_result.selected_players}
                    filtered_players = [players[i] for i in selected_ids if i < len(players)]
                    players_by_country[country_code] = filtered_players
                    result.players_filtered = len(filtered_players)

        # Phase 3: Export
        export_result = ExportResult(
            country_results=country_results,
            export_paths={fmt: [] for fmt in formats},
        )

        export_start = time.time()

        try:
            # Export to all requested formats
            export_paths = self.exporter.export_all(
                players_by_country=players_by_country,
                formats=formats,
            )
            export_result.export_paths = export_paths
            export_result.total_players_exported = sum(
                len(players) for players in players_by_country.values()
            )

        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            export_result.errors.append(error_msg)

        export_result.export_time = time.time() - export_start

        # Log summary
        summary = export_result.get_summary()
        logger.info(
            f"Export complete: {summary['total_players_exported']} players exported "
            f"in {summary['export_time_seconds']:.2f}s"
        )

        return export_result

    def export_existing(
        self,
        players_by_country: Dict[str, List[YouthPlayer]],
        formats: Optional[List[str]] = None,
    ) -> ExportResult:
        """Export existing players without regeneration.

        Useful for re-exporting previously generated players to different formats.

        Args:
            players_by_country: Dictionary mapping country codes to player lists
            formats: List of export formats (default: from config)

        Returns:
            ExportResult with export paths and statistics
        """
        if formats is None:
            formats = [f.value for f in self.config.export.formats]
        formats = [f.lower() for f in formats]

        logger.info(f"Exporting existing players to formats: {formats}")

        export_result = ExportResult(
            country_results={},  # No generation results since we're just exporting
            export_paths={fmt: [] for fmt in formats},
        )

        export_start = time.time()

        try:
            export_paths = self.exporter.export_all(
                players_by_country=players_by_country,
                formats=formats,
            )
            export_result.export_paths = export_paths
            export_result.total_players_exported = sum(
                len(players) for players in players_by_country.values()
            )

        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            export_result.errors.append(error_msg)

        export_result.export_time = time.time() - export_start

        return export_result


def create_orchestrator(config_path: Optional[str] = None) -> YouthGenerationOrchestrator:
    """Factory function to create a configured orchestrator.

    Args:
        config_path: Path to YAML config file (default: built-in config)

    Returns:
        Configured YouthGenerationOrchestrator instance

    Example:
        >>> orchestrator = create_orchestrator("config/my_config.yaml")
        >>> result = orchestrator.generate_for_country("ENG")
    """
    if config_path:
        config = YouthGenerationConfig.load(config_path)
    else:
        from fm_manager.config.youth_generation_config import get_default_config

        config = get_default_config()

    return YouthGenerationOrchestrator(config)
