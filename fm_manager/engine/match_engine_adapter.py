"""Adapter to use cleaned FM data with the match engine.

This module provides a bridge between the cleaned data and the match engine,
allowing simulations using real player data with full attributes.
"""

import random
from typing import Callable, Optional, Dict, List

from fm_manager.data.cleaned_data_loader import (
    CleanedDataLoaderV2 as CleanedDataLoader,
    PlayerDataFull, ClubDataFull,
    load_for_match_engine
)
from fm_manager.core.models.player import Position
from fm_manager.engine.rotation_system import LineupSelector, MatchImportance


class AdaptedPlayer:
    """Adapter class to make PlayerDataFull compatible with match engine."""
    
    def __init__(self, player_data: PlayerDataFull):
        self._data = player_data
        self.full_name = player_data.name

        # Use intelligent position detection
        best_pos, best_rating = player_data.get_best_position()

        # Smart position correction based on football knowledge
        corrected_position = self._apply_football_intelligence(player_data, best_pos)

        if corrected_position:
            self.position = self._map_to_position_enum(corrected_position)
        else:
            self.position = self._map_to_position_enum(best_pos if best_pos else player_data.position)

        self.nationality = player_data.nationality

        # Use position-specific rating if available
        self.current_ability = int(best_rating) if best_rating > 0 else int(player_data.current_ability)

        # Store primary position for multi-position system
        self.primary_position = self.position

        # Initialize position proficiencies
        self._initialize_position_proficiencies(player_data)
        
        # Map position ratings to general attributes
        if self.position in {Position.ST, Position.CF, Position.LW, Position.RW}:
            self.pace = int(player_data.rating_ts * 0.9) if player_data.rating_ts > 0 else int(player_data.current_ability * 0.8)
            self.shooting = int(player_data.rating_ts * 0.95) if player_data.rating_ts > 0 else int(player_data.current_ability * 0.9)
            self.passing = int(player_data.rating_amc * 0.85) if player_data.rating_amc > 0 else int(player_data.current_ability * 0.7)
            self.dribbling = int(player_data.rating_aml * 0.85) if player_data.rating_aml > 0 else int(player_data.current_ability * 0.8)
            self.tackling = int(player_data.current_ability * 0.4)
            self.marking = int(player_data.current_ability * 0.4)
            self.positioning = int(player_data.rating_ts * 0.8) if player_data.rating_ts > 0 else int(player_data.current_ability * 0.7)
            self.strength = int(player_data.rating_ts * 0.85) if player_data.rating_ts > 0 else int(player_data.current_ability * 0.75)
        elif self.position in {Position.CM, Position.CAM, Position.CDM, Position.LM, Position.RM}:
            self.pace = int(player_data.rating_ml * 0.85) if player_data.rating_ml > 0 else int(player_data.current_ability * 0.75)
            self.shooting = int(player_data.rating_amc * 0.8) if player_data.rating_amc > 0 else int(player_data.current_ability * 0.6)
            self.passing = int(player_data.rating_mc * 0.95) if player_data.rating_mc > 0 else int(player_data.current_ability * 0.9)
            self.dribbling = int(player_data.rating_mc * 0.9) if player_data.rating_mc > 0 else int(player_data.current_ability * 0.85)
            self.tackling = int(player_data.rating_dm * 0.8) if player_data.rating_dm > 0 else int(player_data.current_ability * 0.6)
            self.marking = int(player_data.rating_dm * 0.8) if player_data.rating_dm > 0 else int(player_data.current_ability * 0.6)
            self.positioning = int(player_data.rating_mc * 0.9) if player_data.rating_mc > 0 else int(player_data.current_ability * 0.8)
            self.strength = int(player_data.rating_mc * 0.8) if player_data.rating_mc > 0 else int(player_data.current_ability * 0.75)
        elif self.position in {Position.CB, Position.LB, Position.RB, Position.LWB, Position.RWB}:
            self.pace = int(player_data.rating_dl * 0.85) if player_data.rating_dl > 0 else int(player_data.current_ability * 0.75)
            self.shooting = int(player_data.current_ability * 0.4)
            self.passing = int(player_data.rating_dc * 0.75) if player_data.rating_dc > 0 else int(player_data.current_ability * 0.65)
            self.dribbling = int(player_data.rating_dl * 0.7) if player_data.rating_dl > 0 else int(player_data.current_ability * 0.6)
            self.tackling = int(player_data.rating_dc * 0.95) if player_data.rating_dc > 0 else int(player_data.current_ability * 0.9)
            self.marking = int(player_data.rating_dc * 0.95) if player_data.rating_dc > 0 else int(player_data.current_ability * 0.9)
            self.positioning = int(player_data.rating_dc * 0.9) if player_data.rating_dc > 0 else int(player_data.current_ability * 0.85)
            self.strength = int(player_data.rating_dc * 0.9) if player_data.rating_dc > 0 else int(player_data.current_ability * 0.85)
        elif self.position == Position.GK:
            self.pace = int(player_data.current_ability * 0.6)
            self.shooting = int(player_data.current_ability * 0.3)
            self.passing = int(player_data.rating_gk * 0.8) if player_data.rating_gk > 0 else int(player_data.current_ability * 0.6)
            self.dribbling = int(player_data.current_ability * 0.3)
            self.tackling = int(player_data.rating_gk * 0.85) if player_data.rating_gk > 0 else int(player_data.current_ability * 0.75)
            self.marking = int(player_data.rating_gk * 0.85) if player_data.rating_gk > 0 else int(player_data.current_ability * 0.75)
            self.positioning = int(player_data.rating_gk * 0.95) if player_data.rating_gk > 0 else int(player_data.current_ability * 0.9)
            self.strength = int(player_data.rating_gk * 0.8) if player_data.rating_gk > 0 else int(player_data.current_ability * 0.7)
        else:
            self.pace = int(player_data.current_ability * 0.8)
            self.shooting = int(player_data.current_ability * 0.8)
            self.passing = int(player_data.current_ability * 0.8)
            self.dribbling = int(player_data.current_ability * 0.8)
            self.tackling = int(player_data.current_ability * 0.8)
            self.marking = int(player_data.current_ability * 0.8)
            self.positioning = int(player_data.current_ability * 0.8)
            self.strength = int(player_data.current_ability * 0.8)
        
        self.fitness = max(0, min(100, int(player_data.stamina)))
        self.morale = max(0, min(100, int(player_data.happiness)))
        self.form = max(0, min(100, int(player_data.match_shape)))
        self.age = player_data.age
        self.club_id = player_data.club_id

        # Expose player ID for rotation system
        self.id = player_data.id

    def get_position_rating(self) -> float:
        """Get the position-specific rating for this player."""
        return self._data.get_rating_for_position(self._data.position)
    
    def _map_to_position_enum(self, pos_str: str) -> Position:
        pos_map = {
            "GK": Position.GK, "CB": Position.CB, "LB": Position.LB, "RB": Position.RB,
            "LWB": Position.LWB, "RWB": Position.RWB, "CDM": Position.CDM,
            "CM": Position.CM, "LM": Position.LM, "RM": Position.RM,
            "CAM": Position.CAM, "LW": Position.LW, "RW": Position.RW,
            "CF": Position.CF, "ST": Position.ST,
            "FB": Position.LB, "WB": Position.LWB, "Winger": Position.RW,
            # FM specific positions
            "TS": Position.CF,  # Target Shadow/Striker → Center Forward
            "FS": Position.CF,  # Forward/Second Striker → Center Forward
            "SW": Position.CB,  # Sweeper → Center Back
            "DL": Position.LB, "DC": Position.CB, "DR": Position.RB,
            "WBL": Position.LWB, "WBR": Position.RWB,
            "DM": Position.CDM, "ML": Position.LM, "MC": Position.CM, "MR": Position.RM,
            "AML": Position.LW, "AMC": Position.CAM, "AMR": Position.RW,
        }
        return pos_map.get(pos_str, Position.CM)

    def _apply_football_intelligence(self, player_data: PlayerDataFull, detected_pos: str) -> Optional[str]:
        """
        Apply football knowledge to correct position detection errors.

        This function analyzes a player's position ratings and applies real-world
        football knowledge to identify and fix obvious position detection mistakes.

        Examples of corrections:
        - Bellingham: RW (data) → CM/CAM (reality) - has high mid ratings
        - Vinícius Jr: CAM (data) → LW (reality) - winger characteristics

        Returns:
            Corrected position string, or None if no correction needed
        """
        # Get ratings for key positions
        ratings = {
            'ST': player_data.get_rating_for_position('ST'),
            'CF': player_data.get_rating_for_position('CF'),
            'CAM': player_data.get_rating_for_position('AMC'),
            'CM': player_data.get_rating_for_position('MC'),
            'CDM': player_data.get_rating_for_position('DM'),
            'LW': player_data.get_rating_for_position('AML'),
            'RW': player_data.get_rating_for_position('AMR'),
            'LB': player_data.get_rating_for_position('DL'),
            'RB': player_data.get_rating_for_position('DR'),
            'CB': player_data.get_rating_for_position('DC'),
        }

        # Sort positions by rating (descending)
        sorted_positions = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
        best_pos, best_rating = sorted_positions[0]
        second_best_pos, second_best_rating = sorted_positions[1] if len(sorted_positions) > 1 else (best_pos, 0)

        # Case 1: Winger vs Central Midfielder (Bellingham case)
        # If detected as winger but has equally high midfield ratings, correct to CM/CAM
        if detected_pos in ['RW', 'LW', 'AMR', 'AML']:
            midfield_avg = (ratings['CM'] + ratings['CAM'] + ratings['CDM']) / 3
            winger_avg = (ratings['LW'] + ratings['RW']) / 2

            # If midfield ratings are close to winger ratings (within 5%), likely a midfielder
            if midfield_avg > winger_avg * 0.95:
                # Prefer CM over CAM for box-to-box midfielders
                if ratings['CM'] >= ratings['CAM']:
                    return 'CM'
                else:
                    return 'CAM'

        # Case 2: CAM vs Winger (Vinícius Jr case)
        # If detected as CAM but winger rating is similar, check playing style
        if detected_pos in ['CAM', 'AMC']:
            # Get winger and forward ratings
            lw_rating = ratings['LW']
            rw_rating = ratings['RW']
            st_rating = ratings['ST']
            cf_rating = ratings['CF']

            # If winger ratings are similar to CAM (within 3%), might be a winger
            max_winger_rating = max(lw_rating, rw_rating)
            if max_winger_rating >= best_rating * 0.97 and max_winger_rating > 0:
                # Check if player has forward characteristics (high ST/CF)
                max_forward_rating = max(st_rating, cf_rating)
                if max_forward_rating >= best_rating * 0.90:
                    # Winger/Forward hybrid
                    return 'LW' if lw_rating >= rw_rating else 'RW'

        # Case 3: Forward vs Midfielder
        # If detected as forward but has excellent midfield ratings
        if detected_pos in ['ST', 'CF', 'TS', 'FS']:
            # Check if player is actually a CAM
            if ratings['CAM'] >= best_rating * 0.95 and ratings['CAM'] > ratings['CM']:
                return 'CAM'

        # Case 4: CDM detection
        # Some players are misclassified as CM when they're naturally CDM
        if detected_pos in ['CM', 'MC']:
            # If CDM rating is very high and player has good defensive stats
            if ratings['CDM'] >= best_rating * 0.98:
                # Check defensive positioning (lower rating = better at CDM in FM)
                # If player's best positions are all defensive/midfield
                if best_pos in ['CM', 'CDM', 'CAM'] and ratings['CDM'] > 0:
                    return 'CDM'

        # No correction needed
        return None

    def _initialize_position_proficiencies(self, player_data: PlayerDataFull):
        """
        Initialize multi-position proficiency system based on position ratings.

        This sets up a dictionary mapping positions to proficiency scores (0-100).
        The primary position gets 90, and compatible positions get scores based
        on their rating relative to the primary position.
        """
        # Position compatibility matrix - which positions can a player naturally play?
        # Format: primary_position: [(compatible_pos, max_proficiency), ...]
        compatibilities = {
            Position.ST: [(Position.CF, 85), (Position.CAM, 70), (Position.LW, 70), (Position.RW, 70)],
            Position.CF: [(Position.ST, 85), (Position.CAM, 70), (Position.LW, 65), (Position.RW, 65)],
            Position.CAM: [(Position.CM, 85), (Position.LW, 75), (Position.RW, 75), (Position.ST, 70)],
            Position.CM: [(Position.CAM, 80), (Position.CDM, 75), (Position.LM, 65), (Position.RM, 65)],
            Position.CDM: [(Position.CM, 80), (Position.CB, 60)],
            Position.LW: [(Position.RW, 80), (Position.LM, 75), (Position.CAM, 75)],
            Position.RW: [(Position.LW, 80), (Position.RM, 75), (Position.CAM, 75)],
            Position.LM: [(Position.CM, 75), (Position.LW, 70), (Position.LWB, 70)],
            Position.RM: [(Position.CM, 75), (Position.RW, 70), (Position.RWB, 70)],
            Position.CB: [(Position.LB, 60), (Position.RB, 60), (Position.CDM, 55)],
            Position.LB: [(Position.LWB, 75), (Position.CB, 60)],
            Position.RB: [(Position.RWB, 75), (Position.CB, 60)],
            Position.LWB: [(Position.LB, 80), (Position.LM, 65)],
            Position.RWB: [(Position.RB, 80), (Position.RM, 65)],
        }

        # Initialize proficiencies dictionary
        self.position_proficiencies: Dict[Position, float] = {}

        # Primary position gets base 90
        self.position_proficiencies[self.primary_position] = 90.0

        # Get compatible positions for primary position
        compatible = compatibilities.get(self.primary_position, [])

        # Calculate actual proficiencies based on player's position ratings
        for compat_pos, base_proficiency in compatible:
            # Map position to FM position strings for rating lookup
            pos_to_fm = {
                Position.ST: 'ST', Position.CF: 'CF', Position.CAM: 'AMC',
                Position.CM: 'MC', Position.CDM: 'DM', Position.LW: 'AML',
                Position.RW: 'AMR', Position.LM: 'ML', Position.RM: 'MR',
                Position.CB: 'DC', Position.LB: 'DL', Position.RB: 'DR',
                Position.LWB: 'WBL', Position.RWB: 'WBR',
            }

            fm_pos = pos_to_fm.get(compat_pos, 'MC')
            actual_rating = player_data.get_rating_for_position(fm_pos)

            # Scale proficiency based on actual rating relative to primary
            # If actual rating is close to primary, use higher proficiency
            primary_rating = player_data.get_rating_for_position(
                pos_to_fm.get(self.primary_position, 'MC')
            )

            if actual_rating > 0 and primary_rating > 0:
                rating_ratio = actual_rating / primary_rating
                # Adjust base proficiency by rating ratio (capped at ±15)
                adjusted_proficiency = base_proficiency * rating_ratio
                adjusted_proficiency = max(50, min(95, adjusted_proficiency))
            else:
                adjusted_proficiency = base_proficiency - 10  # Penalty for unknown rating

            self.position_proficiencies[compat_pos] = adjusted_proficiency

    def get_proficiency_for_position(self, position: Position) -> float:
        """
        Get player's proficiency for a specific position.

        Returns:
            Proficiency score (0-100). Returns 50 if position not in proficiencies.
        """
        return self.position_proficiencies.get(position, 50.0)

    def get_proficiency_modifier(self, position: Position) -> float:
        """
        Get attribute modifier for playing at a specific position.

        Returns:
            Modifier multiplier:
            - 90+ proficiency: 1.05 (Master - slight boost)
            - 80-90 proficiency: 1.00 (Comfortable - full potential)
            - 70-80 proficiency: 0.90 (Learning - slight reduction)
            - 60-70 proficiency: 0.80 (Struggling - significant reduction)
            - <60 proficiency: 0.70 (Out of position - major reduction)
        """
        proficiency = self.get_proficiency_for_position(position)

        if proficiency >= 90:
            return 1.05
        elif proficiency >= 80:
            return 1.00
        elif proficiency >= 70:
            return 0.90
        elif proficiency >= 60:
            return 0.80
        else:
            return 0.70


class ClubSquadBuilder:
    """Build balanced squads from club data."""

    FORMATIONS = {
        "4-3-3": {"GK": 1, "DEF": 4, "MID": 3, "ATT": 3},
        "4-4-2": {"GK": 1, "DEF": 4, "MID": 4, "ATT": 2},
        "3-5-2": {"GK": 1, "DEF": 3, "MID": 5, "ATT": 2},
        "4-2-3-1": {"GK": 1, "DEF": 4, "MID": 5, "ATT": 1},
        "5-3-2": {"GK": 1, "DEF": 5, "MID": 3, "ATT": 2},
    }

    POSITION_MAP = {
        "GK": ["GK"],
        "DEF": ["DL", "DC", "DR", "WBL", "WBR", "LB", "RB", "CB", "LWB", "RWB"],
        "MID": ["DM", "ML", "MC", "MR", "CDM", "CM", "LM", "RM"],
        "ATT": ["AML", "AMC", "AMR", "FS", "TS", "CAM", "LW", "RW", "CF", "ST"],
    }

    def __init__(self, club_data: ClubDataFull, enable_rotation: bool = False):
        """
        Initialize squad builder.

        Args:
            club_data: 球队数据
            enable_rotation: 是否启用轮换系统
        """
        self.club = club_data
        self.players_by_position = self._categorize_players()
        self.enable_rotation = enable_rotation

        # 轮换系统
        if enable_rotation:
            # 转换为AdaptedPlayer列表
            adapted_squad = [AdaptedPlayer(p) for p in club_data.players]
            self.rotation_system = LineupSelector(
                squad=adapted_squad,
                formation="4-3-3"
            )
    
    def _categorize_players(self) -> dict[str, list[PlayerDataFull]]:
        categorized = {"GK": [], "DEF": [], "MID": [], "ATT": []}
        
        for player in self.club.players:
            best_cat = "MID"
            best_rating = 0
            
            for cat, positions in self.POSITION_MAP.items():
                for p in positions:
                    rating = player.get_rating_for_position(p)
                    if rating > best_rating:
                        best_rating = rating
                        best_cat = cat
            
            categorized[best_cat].append(player)
        
        for category in categorized:
            categorized[category].sort(
                key=lambda p: max([p.get_rating_for_position(pos) for pos in self.POSITION_MAP[category]] + [0]),
                reverse=True
            )
        
        return categorized
    
    def build_lineup(
        self,
        formation: str = "4-3-3",
        match_importance: MatchImportance = MatchImportance.MEDIUM,
        opponent_strength: float = 70.0,
        is_home: bool = True,
    ) -> list[AdaptedPlayer]:
        """
        构建首发阵容（支持轮换）

        Args:
            formation: 阵型
            match_importance: 比赛重要性（如果启用轮换）
            opponent_strength: 对手实力（如果启用轮换）
            is_home: 是否主场（如果启用轮换）

        Returns:
            11名首发球员
        """
        # 如果启用轮换系统，使用智能选择
        if self.enable_rotation and self.rotation_system:
            # 更新阵型
            self.rotation_system.formation = formation

            # 选择阵容
            selected_players = self.rotation_system.select_lineup(
                importance=match_importance,
                opponent_strength=opponent_strength,
                is_home=is_home,
            )

            # 转换为AdaptedPlayer
            return selected_players

        # 原逻辑：不轮换，总是选择最强的11人
        if formation not in self.FORMATIONS:
            formation = "4-3-3"

        req = self.FORMATIONS[formation].copy()
        lineup = []

        gk_needed = req.pop("GK")
        lineup.extend(self.players_by_position["GK"][:gk_needed])

        def_needed = req.pop("DEF")
        lineup.extend(self.players_by_position["DEF"][:def_needed])

        mid_needed = req.pop("MID")
        lineup.extend(self.players_by_position["MID"][:mid_needed])

        att_needed = req.pop("ATT")
        lineup.extend(self.players_by_position["ATT"][:att_needed])

        while len(lineup) < 11:
            remaining = []
            for category in self.players_by_position:
                used_ids = {p.id for p in lineup}
                remaining.extend([p for p in self.players_by_position[category] if p.id not in used_ids])
            remaining.sort(key=lambda p: p.current_ability, reverse=True)
            if remaining:
                lineup.append(remaining[0])
            else:
                break

        return [AdaptedPlayer(p) for p in lineup[:11]]

    def update_rotation_after_match(
        self,
        lineup: list[AdaptedPlayer],
        minutes_played: Dict[int, int] = None,
    ):
        """
        比赛后更新轮换状态

        Args:
            lineup: 首发阵容
            minutes_played: {player_id: 出场分钟数}，如果为None则假设全部90分钟
        """
        if not self.enable_rotation or not self.rotation_system:
            return

        if minutes_played is None:
            minutes_played = {p.id: 90 for p in lineup}

        # 更新球员状态
        self.rotation_system.update_after_match(
            lineup=lineup,
            minutes_played=minutes_played
        )

    def get_rotation_status(self) -> Dict:
        """获取轮换状态统计"""
        if not self.enable_rotation:
            return {"rotation_enabled": False}

        status = self.rotation_system.get_rotation_status()
        status["rotation_enabled"] = True
        return status
    
    def get_squad_summary(self) -> dict:
        total_players = len(self.club.players)
        if total_players == 0:
            return {"total_players": 0, "avg_ability": 0}
        
        avg_ability = sum(p.current_ability for p in self.club.players) / total_players
        avg_age = sum(p.age for p in self.club.players) / total_players
        best_player = max(self.club.players, key=lambda p: p.current_ability)
        
        return {
            "club_name": self.club.name,
            "league": self.club.league,
            "total_players": total_players,
            "avg_ability": round(avg_ability, 1),
            "avg_age": round(avg_age, 1),
            "goalkeepers": len(self.players_by_position["GK"]),
            "defenders": len(self.players_by_position["DEF"]),
            "midfielders": len(self.players_by_position["MID"]),
            "attackers": len(self.players_by_position["ATT"]),
            "best_player": best_player.name if best_player else "N/A",
            "best_ability": round(best_player.current_ability, 1) if best_player else 0,
        }


class MatchSimulatorWithRealData:
    """Match simulator that uses cleaned FM data."""
    
    def __init__(self, random_seed: Optional[int] = None):
        self.rng = random.Random(random_seed)
        self._loader: Optional[CleanedDataLoader] = None
        self._clubs: dict[int, ClubDataFull] = {}
        self._players: dict[int, PlayerDataFull] = {}
    
    def load_data(self) -> None:
        print("Loading cleaned FM data...")
        self._clubs, self._players = load_for_match_engine()
        print(f"Loaded {len(self._clubs)} clubs and {len(self._players)} players")
    
    def simulate_match(
        self,
        home_club_id: int,
        away_club_id: int,
        home_formation: str = "4-3-3",
        away_formation: str = "4-3-3",
        callback: Optional[Callable] = None,
    ) -> dict:
        if not self._clubs:
            self.load_data()
        
        home_club = self._clubs.get(home_club_id)
        away_club = self._clubs.get(away_club_id)
        
        if not home_club or not away_club:
            raise ValueError(f"Club not found: {home_club_id} or {away_club_id}")
        
        home_builder = ClubSquadBuilder(home_club)
        away_builder = ClubSquadBuilder(away_club)
        
        home_lineup = home_builder.build_lineup(home_formation)
        away_lineup = away_builder.build_lineup(away_formation)
        
        from fm_manager.engine.match_engine_realistic import RealisticMatchSimulator
        
        simulator = RealisticMatchSimulator(random_seed=self.rng.randint(0, 1000000))
        state = simulator.simulate(
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            home_formation=home_formation,
            away_formation=away_formation,
            callback=callback,
        )
        
        return {
            "home_club": home_club.name,
            "away_club": away_club.name,
            "home_score": state.home_score,
            "away_score": state.away_score,
            "score": state.score_string(),
            "winner": state.winning_team(),
            "events": [
                {
                    "minute": e.minute,
                    "type": e.event_type.name,
                    "team": e.team,
                    "player": e.player,
                    "description": e.description,
                }
                for e in state.events
            ],
            "stats": {
                "home_shots": state.home_shots,
                "home_shots_on_target": state.home_shots_on_target,
                "away_shots": state.away_shots,
                "away_shots_on_target": state.away_shots_on_target,
                "home_possession": round(state.home_possession, 1),
                "away_possession": round(100 - state.home_possession, 1),
            }
        }
    
    def find_club(self, name_query: str) -> Optional[ClubDataFull]:
        if not self._clubs:
            self.load_data()
        
        for club in self._clubs.values():
            if name_query.lower() == club.name.lower():
                return club
        
        for club in self._clubs.values():
            if name_query.lower() in club.name.lower():
                return club
        
        return None
    
    def list_clubs_in_league(self, league_name: str) -> list[ClubDataFull]:
        if not self._clubs:
            self.load_data()
        return [c for c in self._clubs.values() if c.league == league_name]
    
    def get_available_leagues(self) -> list[str]:
        if not self._clubs:
            self.load_data()
        leagues = {c.league for c in self._clubs.values()}
        return sorted(list(leagues))


def simulate_match_between(
    home_club_name: str,
    away_club_name: str,
    home_formation: str = "4-3-3",
    away_formation: str = "4-3-3",
    random_seed: Optional[int] = None,
) -> dict:
    simulator = MatchSimulatorWithRealData(random_seed=random_seed)
    simulator.load_data()
    
    home_club = simulator.find_club(home_club_name)
    away_club = simulator.find_club(away_club_name)
    
    if not home_club:
        raise ValueError(f"Home club not found: {home_club_name}")
    if not away_club:
        raise ValueError(f"Away club not found: {away_club_name}")
    
    return simulator.simulate_match(
        home_club_id=home_club.id,
        away_club_id=away_club.id,
        home_formation=home_formation,
        away_formation=away_formation,
    )


def get_premier_league_clubs() -> list[ClubDataFull]:
    simulator = MatchSimulatorWithRealData()
    simulator.load_data()
    return simulator.list_clubs_in_league("England Premier League")
