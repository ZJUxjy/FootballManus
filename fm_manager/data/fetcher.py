"""Data fetching from external APIs."""

import asyncio
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from fm_manager.core.config import settings


class FootballDataAPI:
    """Client for football-data.org API."""
    
    BASE_URL = "https://api.football-data.org/v4"
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.football_data_api_key
        self.headers = {"X-Auth-Token": self.api_key} if self.api_key else {}
        self.client: httpx.AsyncClient | None = None
    
    async def __aenter__(self) -> "FootballDataAPI":
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self.headers,
            timeout=30.0,
        )
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Make a GET request with retry logic."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_competitions(self) -> list[dict]:
        """Get list of available competitions."""
        data = await self._get("/competitions")
        return data.get("competitions", [])
    
    async def get_teams(self, competition_code: str) -> list[dict]:
        """Get teams in a competition."""
        data = await self._get(f"/competitions/{competition_code}/teams")
        return data.get("teams", [])
    
    async def get_team_squad(self, team_id: int) -> list[dict]:
        """Get squad of a team."""
        data = await self._get(f"/teams/{team_id}")
        return data.get("squad", [])
    
    async def get_matches(
        self,
        competition_code: str,
        matchday: int | None = None,
    ) -> list[dict]:
        """Get matches for a competition."""
        params = {}
        if matchday:
            params["matchday"] = matchday
        data = await self._get(f"/competitions/{competition_code}/matches", params)
        return data.get("matches", [])


class APIFootballClient:
    """Client for API-Football."""
    
    BASE_URL = "https://v3.football.api-sports.io"
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.api_football_key
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "v3.football.api-sports.io",
        }
        self.client: httpx.AsyncClient | None = None
    
    async def __aenter__(self) -> "APIFootballClient":
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self.headers,
            timeout=30.0,
        )
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Make a GET request with retry logic."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        response = await self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_leagues(self) -> list[dict]:
        """Get list of leagues."""
        data = await self._get("/leagues")
        return data.get("response", [])
    
    async def get_teams(self, league_id: int, season: int) -> list[dict]:
        """Get teams in a league."""
        params = {"league": league_id, "season": season}
        data = await self._get("/teams", params)
        return data.get("response", [])
    
    async def get_players(
        self,
        team_id: int,
        season: int,
        page: int = 1,
    ) -> dict:
        """Get players of a team."""
        params = {"team": team_id, "season": season, "page": page}
        data = await self._get("/players", params)
        return data


class DataFetcher:
    """High-level data fetching coordinator."""
    
    def __init__(self):
        self.football_data = FootballDataAPI()
        self.api_football = APIFootballClient()
    
    async def fetch_league_data(
        self,
        league_code: str,
        season: int,
    ) -> dict[str, Any]:
        """Fetch complete data for a league."""
        result = {
            "league": None,
            "teams": [],
            "players": [],
        }
        
        async with self.football_data:
            # Get teams
            teams = await self.football_data.get_teams(league_code)
            result["teams"] = teams
            
            # Get players for each team
            for team in teams:
                team_id = team.get("id")
                if team_id:
                    squad = await self.football_data.get_team_squad(team_id)
                    result["players"].extend([
                        {**player, "team_id": team_id}
                        for player in squad
                    ])
        
        return result


# Convenience function
async def fetch_sample_data() -> dict[str, Any]:
    """Fetch sample data for testing."""
    fetcher = DataFetcher()
    # Fetch Premier League data as sample
    return await fetcher.fetch_league_data("PL", 2024)
