#!/usr/bin/env python3
"""Multi-slot save/load system for FM Manager.

Provides 10 save slots with:
- Slot management
- Auto-save
- Quick save/load
- Save metadata
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class SaveSlot:
    """Represents a save slot."""
    slot_number: int
    save_name: str = ""
    save_date: Optional[datetime] = None
    season: int = 1
    week: int = 1
    club_id: Optional[int] = None
    club_name: str = ""
    has_save: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_number": self.slot_number,
            "save_name": self.save_name,
            "save_date": self.save_date.isoformat() if self.save_date else None,
            "season": self.season,
            "week": self.week,
            "club_id": self.club_id,
            "club_name": self.club_name,
            "has_save": self.has_save
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SaveSlot":
        save_date = data.get("save_date")
        if save_date:
            save_date = datetime.fromisoformat(save_date)
        
        return cls(
            slot_number=data.get("slot_number", 0),
            save_name=data.get("save_name", ""),
            save_date=save_date,
            season=data.get("season", 1),
            week=data.get("week", 1),
            club_id=data.get("club_id"),
            club_name=data.get("club_name", ""),
            has_save=data.get("has_save", False)
        )


class SlotSaveManager:
    """Manage 10 save slots for game state."""
    
    NUM_SLOTS = 10
    
    def __init__(self, save_dir: Optional[Path] = None):
        if save_dir is None:
            save_dir = Path.home() / ".fm_manager" / "saves"
        self.save_dir = Path(save_dir) if isinstance(save_dir, str) else save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.save_dir / "slots_metadata.json"
        self._ensure_slots_exist()
    
    def _ensure_slots_exist(self):
        """Ensure all slot files exist."""
        for i in range(1, self.NUM_SLOTS + 1):
            slot_file = self.save_dir / f"slot_{i:02d}.json"
            if not slot_file.exists():
                self._create_empty_slot(i)
    
    def _create_empty_slot(self, slot_num: int):
        """Create an empty slot file."""
        slot_file = self.save_dir / f"slot_{slot_num:02d}.json"
        slot_data = {
            "slot_number": slot_num,
            "save_name": "",
            "save_date": None,
            "season": 1,
            "week": 1,
            "club_id": None,
            "club_name": "",
            "game_state": None
        }
        with open(slot_file, 'w') as f:
            json.dump(slot_data, f, indent=2)
    
    def get_slot(self, slot_num: int) -> SaveSlot:
        """Get slot info without loading full game state."""
        if not 1 <= slot_num <= self.NUM_SLOTS:
            raise ValueError(f"Invalid slot number: {slot_num}")
        
        slot_file = self.save_dir / f"slot_{slot_num:02d}.json"
        
        if not slot_file.exists():
            return SaveSlot(slot_number=slot_num)
        
        with open(slot_file, 'r') as f:
            data = json.load(f)
        
        has_save = data.get("game_state") is not None
        
        save_date = data.get("save_date")
        if save_date:
            save_date = datetime.fromisoformat(save_date)
        
        return SaveSlot(
            slot_number=slot_num,
            save_name=data.get("save_name", ""),
            save_date=save_date,
            season=data.get("season", 1),
            week=data.get("week", 1),
            club_id=data.get("club_id"),
            club_name=data.get("club_name", ""),
            has_save=has_save
        )
    
    def get_all_slots(self) -> List[SaveSlot]:
        """Get info for all slots."""
        return [self.get_slot(i) for i in range(1, self.NUM_SLOTS + 1)]
    
    def save_to_slot(
        self,
        slot_num: int,
        save_name: str,
        season: int,
        week: int,
        club_id: Optional[int] = None,
        club_name: str = "",
        standings: Optional[Dict] = None,
        match_results: Optional[List] = None,
        extra_data: Optional[Dict] = None
    ) -> bool:
        """Save game state to a slot."""
        if not 1 <= slot_num <= self.NUM_SLOTS:
            return False
        
        slot_file = self.save_dir / f"slot_{slot_num:02d}.json"
        
        serializable_standings = self._serialize_standings(standings)
        
        slot_data = {
            "slot_number": slot_num,
            "save_name": save_name,
            "save_date": datetime.now().isoformat(),
            "season": season,
            "week": week,
            "club_id": club_id,
            "club_name": club_name,
            "game_state": {
                "standings": serializable_standings,
                "match_results": match_results or [],
                "extra": extra_data or {}
            }
        }
        
        with open(slot_file, 'w') as f:
            json.dump(slot_data, f, indent=2, default=str)
        
        return True
    
    def _serialize_standings(self, standings: Optional[Dict]) -> List[Dict]:
        """Convert standings to serializable format."""
        if not standings:
            return []
        
        result = []
        for club_id, data in standings.items():
            club = data.get("club")
            result.append({
                "club_id": club_id,
                "club_name": club.name if club else f"Club {club_id}",
                "played": data.get("played", 0),
                "won": data.get("won", 0),
                "drawn": data.get("drawn", 0),
                "lost": data.get("lost", 0),
                "gf": data.get("gf", 0),
                "ga": data.get("ga", 0),
                "points": data.get("points", 0)
            })
        
        return result
    
    def load_from_slot(self, slot_num: int) -> Optional[Dict[str, Any]]:
        """Load game state from a slot."""
        if not 1 <= slot_num <= self.NUM_SLOTS:
            return None
        
        slot_file = self.save_dir / f"slot_{slot_num:02d}.json"
        
        if not slot_file.exists():
            return None
        
        with open(slot_file, 'r') as f:
            data = json.load(f)
        
        if not data.get("game_state"):
            return None
        
        game_state = data["game_state"]
        
        return {
            "save_name": data.get("save_name", ""),
            "save_date": data.get("save_date"),
            "season": data.get("season", 1),
            "week": data.get("week", 1),
            "club_id": data.get("club_id"),
            "club_name": data.get("club_name", ""),
            "standings": self._deserialize_standings(game_state.get("standings", [])),
            "match_results": game_state.get("match_results", []),
            "extra": game_state.get("extra", {})
        }
    
    def _deserialize_standings(self, standings_list: List[Dict]) -> Dict[int, Dict]:
        """Convert serialized standings back to dict format."""
        result = {}
        for s in standings_list:
            club_id = s.get("club_id")
            result[club_id] = {
                "club_name": s.get("club_name"),
                "played": s.get("played", 0),
                "won": s.get("won", 0),
                "drawn": s.get("drawn", 0),
                "lost": s.get("lost", 0),
                "gf": s.get("gf", 0),
                "ga": s.get("ga", 0),
                "points": s.get("points", 0)
            }
        return result
    
    def delete_slot(self, slot_num: int) -> bool:
        """Delete a save slot."""
        if not 1 <= slot_num <= self.NUM_SLOTS:
            return False
        
        self._create_empty_slot(slot_num)
        return True
    
    def copy_slot(self, src_slot: int, dst_slot: int) -> bool:
        """Copy a save from one slot to another."""
        if not (1 <= src_slot <= self.NUM_SLOTS and 1 <= dst_slot <= self.NUM_SLOTS):
            return False
        
        src_file = self.save_dir / f"slot_{src_slot:02d}.json"
        dst_file = self.save_dir / f"slot_{dst_slot:02d}.json"
        
        if not src_file.exists():
            return False
        
        with open(src_file, 'r') as f:
            data = json.load(f)
        
        data["slot_number"] = dst_slot
        data["save_date"] = datetime.now().isoformat()
        
        with open(dst_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return True
    
    def quick_save(self, season: int, week: int, club_id: Optional[int] = None, 
                   standings: Optional[Dict] = None, match_results: Optional[List] = None) -> int:
        """Quick save to slot 10 (reserved for quick saves)."""
        save_name = f"Quick_S{season}W{week}"
        self.save_to_slot(
            10,
            save_name=save_name,
            season=season,
            week=week,
            club_id=club_id,
            standings=standings,
            match_results=match_results
        )
        return 10
    
    def quick_load(self) -> Optional[Dict[str, Any]]:
        """Quick load from slot 10."""
        return self.load_from_slot(10)
    
    def auto_save(self, season: int, week: int, club_id: Optional[int] = None,
                  standings: Optional[Dict] = None, match_results: Optional[List] = None) -> int:
        """Auto save to slot 9 (reserved for auto saves)."""
        save_name = f"Auto_S{season}W{week}"
        self.save_to_slot(
            9,
            save_name=save_name,
            season=season,
            week=week,
            club_id=club_id,
            standings=standings,
            match_results=match_results
        )
        return 9
    
    def get_latest_save(self) -> Optional[SaveSlot]:
        """Get the most recent save slot."""
        slots = [s for s in self.get_all_slots() if s.has_save]
        if not slots:
            return None
        return max(slots, key=lambda s: s.save_date or datetime.min)
    
    def get_total_saves(self) -> int:
        """Get total number of saves."""
        return sum(1 for s in self.get_all_slots() if s.has_save)
    
    def get_save_storage_size(self) -> int:
        """Get total storage used by saves in bytes."""
        total = 0
        for i in range(1, self.NUM_SLOTS + 1):
            slot_file = self.save_dir / f"slot_{i:02d}.json"
            if slot_file.exists():
                total += slot_file.stat().st_size
        return total
