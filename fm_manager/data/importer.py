"""Import data from external sources into the database."""

import json
from datetime import datetime, date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from fm_manager.core.models import (
    Player, Club, League, Season, Position, LeagueFormat, ClubReputation
)


class DataImporter:
    """Import football data into the database."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def import_leagues(self, leagues_data: list[dict]) -> list[League]:
        """Import leagues into database."""
        leagues = []
        for data in leagues_data:
            league = League(
                name=data["name"],
                short_name=data.get("short_name", data["name"][:3].upper()),
                country=data.get("country", "Unknown"),
                tier=data.get("tier", 1),
                teams_count=data.get("teams_count", 20),
                format=LeagueFormat(data.get("format", "double_round_robin")),
                promotion_count=data.get("promotion_count", 3),
                relegation_count=data.get("relegation_count", 3),
            )
            self.session.add(league)
            leagues.append(league)
        
        await self.session.commit()
        return leagues
    
    async def import_clubs(self, clubs_data: list[dict]) -> list[Club]:
        """Import clubs into database."""
        clubs = []
        for data in clubs_data:
            club = Club(
                name=data["name"],
                short_name=data.get("short_name", data["name"][:3].upper()),
                city=data.get("city", ""),
                country=data.get("country", ""),
                stadium_name=data.get("stadium_name", ""),
                stadium_capacity=data.get("stadium_capacity", 30000),
                reputation=data.get("reputation", 1000),
                reputation_level=ClubReputation(data.get("reputation_level", 3)),
                balance=data.get("balance", 10_000_000),
                transfer_budget=data.get("transfer_budget", 5_000_000),
                wage_budget=data.get("wage_budget", 500_000),
                ticket_price=data.get("ticket_price", 50),
                league_id=data.get("league_id"),
            )
            self.session.add(club)
            clubs.append(club)
        
        await self.session.commit()
        return clubs
    
    async def import_players(self, players_data: list[dict]) -> list[Player]:
        """Import players into database."""
        players = []
        for data in players_data:
            # Map position string to enum
            position_str = data.get("position", "CM")
            try:
                position = Position(position_str.upper())
            except ValueError:
                position = Position.CM  # Default to central midfielder
            
            player = Player(
                first_name=data.get("first_name", data.get("name", "").split()[0]),
                last_name=data.get("last_name", " ".join(data.get("name", "").split()[1:])),
                nationality=data.get("nationality", "Unknown"),
                position=position,
                birth_date=self._parse_date(data.get("date_of_birth")),
                # Attributes
                current_ability=data.get("current_ability", 50),
                potential_ability=data.get("potential_ability", 60),
                # Club
                club_id=data.get("club_id"),
                salary=data.get("salary", 1000),
                market_value=data.get("market_value", 100_000),
                contract_until=self._parse_date(data.get("contract_until")),
            )
            
            # Set specific attributes if provided
            for attr in [
                "pace", "shooting", "passing", "dribbling", "defending",
                "physical", "vision", "decisions", "stamina"
            ]:
                if attr in data:
                    setattr(player, attr, data[attr])
            
            self.session.add(player)
            players.append(player)
        
        await self.session.commit()
        return players
    
    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            if isinstance(date_str, str):
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            return date_str
        except (ValueError, TypeError):
            return None
    
    async def import_from_json(self, json_file: str) -> dict[str, list]:
        """Import data from a JSON file."""
        with open(json_file, "r") as f:
            data = json.load(f)
        
        result = {
            "leagues": [],
            "clubs": [],
            "players": [],
        }
        
        if "leagues" in data:
            result["leagues"] = await self.import_leagues(data["leagues"])
        
        if "clubs" in data:
            result["clubs"] = await self.import_clubs(data["clubs"])
        
        if "players" in data:
            result["players"] = await self.import_players(data["players"])
        
        return result
