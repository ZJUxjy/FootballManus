"""Load cleaned FM data with full attributes."""

import re
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


POSITION_MAPPING = {
    "门将": "GK",
    "后卫 中": "CB",
    "后卫 左": "LB", 
    "后卫 右": "RB",
    "后卫 右中": "CB",
    "后卫 左中": "CB",
    "翼卫 左": "LWB",
    "翼卫 右": "RWB",
    "后腰": "CDM",
    "中场 中": "CM",
    "中场 左": "LM",
    "中场 右": "RM",
    "攻击型中场 中": "CAM",
    "攻击型中场 左": "LW",
    "攻击型中场 右": "RW",
    "攻击型中场 右左": "CAM",
    "攻击型中场 右左中": "CAM",
    "前锋": "ST",
    "中锋": "ST",
    "影子前锋": "CF",
    "边锋": "Winger",
    "后卫/翼卫 左": "LB",
    "后卫/翼卫 右": "RB",
    "攻击型中场 右左, 前锋": "CAM",
    "攻击型中场/前锋 中": "CAM",
}


def map_position(pos_str: str) -> str:
    """Map Chinese position string to English position code.
    
    Longer matches are prioritized to avoid partial matches.
    For example, "攻击型中场 右左中" should match "CAM" not "RW".
    """
    pos_str = str(pos_str).strip() if pos_str else ""
    
    # Sort by length (descending) to prioritize longer matches
    sorted_mappings = sorted(POSITION_MAPPING.items(), key=lambda x: len(x[0]), reverse=True)
    
    for cn_pos, en_pos in sorted_mappings:
        if cn_pos in pos_str:
            return en_pos
    return "CM"


@dataclass
class PlayerDataFull:
    id: int
    name: str
    nationality: str
    age: int
    birth_date: str
    position: str
    location: str
    current_ability: float
    potential_ability: float
    player_role: str
    estimated_role: str
    rating_gk: float = 0.0
    rating_sw: float = 0.0
    rating_dl: float = 0.0
    rating_dc: float = 0.0
    rating_dr: float = 0.0
    rating_wbl: float = 0.0
    rating_wbr: float = 0.0
    rating_dm: float = 0.0
    rating_ml: float = 0.0
    rating_mc: float = 0.0
    rating_mr: float = 0.0
    rating_aml: float = 0.0
    rating_amc: float = 0.0
    rating_amr: float = 0.0
    rating_fs: float = 0.0
    rating_ts: float = 0.0
    potential_gk: float = 0.0
    potential_sw: float = 0.0
    potential_dl: float = 0.0
    potential_dc: float = 0.0
    potential_dr: float = 0.0
    potential_wbl: float = 0.0
    potential_wbr: float = 0.0
    potential_dm: float = 0.0
    potential_ml: float = 0.0
    potential_mc: float = 0.0
    potential_mr: float = 0.0
    potential_aml: float = 0.0
    potential_amc: float = 0.0
    potential_amr: float = 0.0
    potential_fs: float = 0.0
    potential_ts: float = 0.0
    fatigue: int = 0
    stamina: float = 100.0
    match_shape: float = 50.0
    happiness: int = 50
    match_experience: float = 0.0
    intl_caps: int = 0
    intl_goals: int = 0
    market_value: int = 0
    weekly_wage: int = 0
    club_id: int = -1
    club_name: str = ""
    club_reputation: int = 0
    squad_status: str = ""
    
    @property
    def full_name(self) -> str:
        return self.name
    
    @property
    def is_goalkeeper(self) -> bool:
        return self.position == "GK"
    
    def get_rating_for_position(self, pos: str) -> float:
        pos_ratings = {
            "GK": self.rating_gk, "SW": self.rating_sw,
            "DL": self.rating_dl, "LB": self.rating_dl,
            "DC": self.rating_dc, "CB": self.rating_dc,
            "DR": self.rating_dr, "RB": self.rating_dr,
            "WBL": self.rating_wbl, "LWB": self.rating_wbl,
            "WBR": self.rating_wbr, "RWB": self.rating_wbr,
            "DM": self.rating_dm, "CDM": self.rating_dm,
            "ML": self.rating_ml, "LM": self.rating_ml,
            "MC": self.rating_mc, "CM": self.rating_mc,
            "MR": self.rating_mr, "RM": self.rating_mr,
            "AML": self.rating_aml, "LW": self.rating_aml,
            "AMC": self.rating_amc, "CAM": self.rating_amc,
            "AMR": self.rating_amr, "RW": self.rating_amr,
            "FS": self.rating_fs, "CF": self.rating_fs,
            "TS": self.rating_ts, "ST": self.rating_ts,
        }
        return pos_ratings.get(pos, self.current_ability)
    
    def get_best_position(self) -> tuple[str, float]:
        positions = {
            "GK": self.rating_gk, "SW": self.rating_sw,
            "DL": self.rating_dl, "DC": self.rating_dc, "DR": self.rating_dr,
            "WBL": self.rating_wbl, "WBR": self.rating_wbr,
            "DM": self.rating_dm, "ML": self.rating_ml, "MC": self.rating_mc, "MR": self.rating_mr,
            "AML": self.rating_aml, "AMC": self.rating_amc, "AMR": self.rating_amr,
            "FS": self.rating_fs, "TS": self.rating_ts,
        }
        return max(positions.items(), key=lambda x: x[1])


@dataclass
class ClubDataFull:
    id: int
    name: str
    country: str
    league: str
    reputation: int = 1000
    avg_age: float = 25.0
    balance: int = 0
    transfer_budget: int = 0
    wage_budget: int = 0
    stadium_capacity: int = 30000
    avg_attendance: int = 0
    players: list[PlayerDataFull] = field(default_factory=list)
    
    @property
    def squad_size(self) -> int:
        return len(self.players)


class CleanedDataLoaderV2:
    def __init__(self, data_dir: str = "data/cleaned"):
        self.data_dir = Path(data_dir)
        self.players_df: Optional[pd.DataFrame] = None
        self.teams_df: Optional[pd.DataFrame] = None
        self.clubs: dict[int, ClubDataFull] = {}
        self.players: dict[int, PlayerDataFull] = {}
    
    def load_all(self) -> tuple[dict[int, ClubDataFull], dict[int, PlayerDataFull]]:
        self._load_players()
        self._load_teams()
        self._build_clubs()
        return self.clubs, self.players
    
    def _load_players(self) -> None:
        players_path = self.data_dir / "players_cleaned.csv"
        if not players_path.exists():
            raise FileNotFoundError(f"Players file not found: {players_path}")
        
        self.players_df = pd.read_csv(players_path)
        print(f"Loaded {len(self.players_df)} players from {players_path}")
        
        for _, row in self.players_df.iterrows():
            try:
                player = self._parse_player_row(row)
                self.players[player.id] = player
            except Exception as e:
                continue
    
    def _load_teams(self) -> None:
        teams_path = self.data_dir / "teams_cleaned.csv"
        if not teams_path.exists():
            raise FileNotFoundError(f"Teams file not found: {teams_path}")
        
        self.teams_df = pd.read_csv(teams_path)
        print(f"Loaded {len(self.teams_df)} teams from {teams_path}")
    
    def _parse_player_row(self, row: pd.Series) -> PlayerDataFull:
        position = map_position(str(row.get('position', '')))
        
        def get_float(col, default=0.0):
            val = row.get(col, default)
            try:
                return float(val) if pd.notna(val) else default
            except:
                return default
        
        def get_int(col, default=0):
            val = row.get(col, default)
            try:
                return int(val) if pd.notna(val) else default
            except:
                return default
        
        return PlayerDataFull(
            id=get_int('player_id'),
            name=str(row.get('name', 'Unknown')),
            nationality=str(row.get('nationality', 'Unknown')),
            age=get_int('age'),
            birth_date=str(row.get('birth_date', '')),
            position=position,
            location=str(row.get('location', '')),
            current_ability=get_float('current_ability'),
            potential_ability=get_float('potential_ability'),
            player_role=str(row.get('player_role', '')),
            estimated_role=str(row.get('estimated_role', '')),
            rating_gk=get_float('rating_gk'),
            rating_sw=get_float('rating_sw'),
            rating_dl=get_float('rating_dl'),
            rating_dc=get_float('rating_dc'),
            rating_dr=get_float('rating_dr'),
            rating_wbl=get_float('rating_wbl'),
            rating_wbr=get_float('rating_wbr'),
            rating_dm=get_float('rating_dm'),
            rating_ml=get_float('rating_ml'),
            rating_mc=get_float('rating_mc'),
            rating_mr=get_float('rating_mr'),
            rating_aml=get_float('rating_aml'),
            rating_amc=get_float('rating_amc'),
            rating_amr=get_float('rating_amr'),
            rating_fs=get_float('rating_fs'),
            rating_ts=get_float('rating_ts'),
            potential_gk=get_float('potential_gk'),
            potential_sw=get_float('potential_sw'),
            potential_dl=get_float('potential_dl'),
            potential_dc=get_float('potential_dc'),
            potential_dr=get_float('potential_dr'),
            potential_wbl=get_float('potential_wbl'),
            potential_wbr=get_float('potential_wbr'),
            potential_dm=get_float('potential_dm'),
            potential_ml=get_float('potential_ml'),
            potential_mc=get_float('potential_mc'),
            potential_mr=get_float('potential_mr'),
            potential_aml=get_float('potential_aml'),
            potential_amc=get_float('potential_amc'),
            potential_amr=get_float('potential_amr'),
            potential_fs=get_float('potential_fs'),
            potential_ts=get_float('potential_ts'),
            fatigue=get_int('fatigue'),
            stamina=get_float('stamina', 100.0),
            match_shape=get_float('match_shape', 50.0),
            happiness=get_int('happiness', 50),
            match_experience=get_float('match_experience'),
            intl_caps=get_int('intl_caps'),
            intl_goals=get_int('intl_goals'),
            market_value=get_int('value'),
            weekly_wage=get_int('wage'),
            club_id=get_int('club_id', -1),
            club_name=str(row.get('club_name', '')),
            club_reputation=get_int('club_reputation'),
            squad_status=str(row.get('squad_status', '')),
        )
    
    def _build_clubs(self) -> None:
        if self.teams_df is not None:
            for _, row in self.teams_df.iterrows():
                club_id = int(row.get('club_id', 0))
                self.clubs[club_id] = ClubDataFull(
                    id=club_id,
                    name=str(row.get('name', f'Club_{club_id}')),
                    country=str(row.get('country', 'Unknown')),
                    league=str(row.get('league', 'Unknown')),
                    reputation=int(row.get('reputation', 1000)),
                    avg_age=float(row.get('avg_age', 25.0)),
                    balance=int(row.get('balance', 0)),
                    transfer_budget=int(row.get('transfer_budget', 0)),
                    wage_budget=int(row.get('wage_budget', 0)),
                    stadium_capacity=int(row.get('stadium_capacity', 30000)),
                    avg_attendance=int(row.get('avg_attendance', 0)),
                )
        
        for player in self.players.values():
            if player.club_id in self.clubs:
                self.clubs[player.club_id].players.append(player)
        
        print(f"Built {len(self.clubs)} clubs with squads")
    
    def get_clubs_by_league(self, league_name: str) -> list[ClubDataFull]:
        return [c for c in self.clubs.values() if c.league == league_name]
    
    def get_available_leagues(self) -> list[str]:
        if not self.clubs:
            self.load_all()
        leagues = {c.league for c in self.clubs.values()}
        return sorted(list(leagues))


def load_for_match_engine() -> tuple[dict[int, ClubDataFull], dict[int, PlayerDataFull]]:
    loader = CleanedDataLoaderV2()
    return loader.load_all()
