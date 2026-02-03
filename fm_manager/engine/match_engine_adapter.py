"""Adapter to use cleaned FM data with the match engine.

This module provides a bridge between the cleaned data and the match engine,
allowing simulations using real player data with full attributes.
"""

import random
from typing import Callable, Optional

from fm_manager.data.cleaned_data_loader import (
    CleanedDataLoaderV2 as CleanedDataLoader, 
    PlayerDataFull, ClubDataFull, 
    load_for_match_engine
)
from fm_manager.core.models.player import Position


class AdaptedPlayer:
    """Adapter class to make PlayerDataFull compatible with match engine."""
    
    def __init__(self, player_data: PlayerDataFull):
        self._data = player_data
        self.full_name = player_data.name
        self.position = self._map_to_position_enum(player_data.position)
        self.nationality = player_data.nationality
        
        # Use position-specific rating if available
        best_pos, best_rating = player_data.get_best_position()
        self.current_ability = int(best_rating) if best_rating > 0 else int(player_data.current_ability)
        
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
        }
        return pos_map.get(pos_str, Position.CM)


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
    
    def __init__(self, club_data: ClubDataFull):
        self.club = club_data
        self.players_by_position = self._categorize_players()
    
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
    
    def build_lineup(self, formation: str = "4-3-3") -> list[AdaptedPlayer]:
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
