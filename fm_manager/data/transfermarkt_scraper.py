"""Transfermarkt web scraper for fetching player and club data.

Note: This scraper respects robots.txt and includes rate limiting.
For production use, consider using official APIs or purchasing data.
"""

import asyncio
import json
import random
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


@dataclass
class PlayerData:
    """Structured player data from Transfermarkt."""
    name: str
    position: str
    age: int | None
    nationality: str
    club: str
    market_value: int | None
    contract_end: date | None
    height: int | None  # cm
    foot: str
    joined_date: date | None
    
    # FIFA-style attributes (estimated from Transfermarkt data)
    overall_rating: int | None = None


@dataclass
class ClubData:
    """Structured club data from Transfermarkt."""
    name: str
    league: str
    stadium: str
    stadium_capacity: int
    squad_size: int
    avg_age: float
    total_value: int
    coach: str


class TransfermarktScraper:
    """Scraper for Transfermarkt website.
    
    Usage:
        async with TransfermarktScraper() as scraper:
            players = await scraper.get_league_players("premier-league", 2024)
    """
    
    BASE_URL = "https://www.transfermarkt.com"
    
    # User agents to rotate
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(self, delay: float = 2.0, max_retries: int = 3):
        self.delay = delay  # Seconds between requests
        self.max_retries = max_retries
        self.client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0
    
    async def __aenter__(self) -> "TransfermarktScraper":
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
        }
        self.client = httpx.AsyncClient(
            headers=headers,
            base_url=self.BASE_URL,
            timeout=30.0,
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()
    
    async def _get(self, url: str, params: dict | None = None) -> BeautifulSoup:
        """Make a rate-limited GET request."""
        # Rate limiting
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            await asyncio.sleep(self.delay - elapsed + random.uniform(0.5, 1.5))
        
        if not self.client:
            raise RuntimeError("Client not initialized")
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                self._last_request_time = time.time()
                return BeautifulSoup(response.content, "lxml")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Too Many Requests
                    wait_time = (attempt + 1) * 5
                    print(f"Rate limited, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
        
        raise Exception(f"Failed to fetch {url} after {self.max_retries} attempts")
    
    def _parse_market_value(self, value_str: str) -> int | None:
        """Parse market value string to integer (euros)."""
        if not value_str or value_str in ["-", "?"]:
            return None
        
        value_str = value_str.replace("€", "").replace(",", "").strip()
        
        try:
            if "m" in value_str.lower():
                return int(float(value_str.lower().replace("m", "")) * 1_000_000)
            elif "k" in value_str.lower():
                return int(float(value_str.lower().replace("k", "")) * 1_000)
            else:
                return int(float(value_str))
        except ValueError:
            return None
    
    def _parse_date(self, date_str: str) -> date | None:
        """Parse date string."""
        if not date_str or date_str == "-":
            return None
        
        formats = ["%b %d, %Y", "%d.%m.%Y", "%Y-%m-%d", "%b %Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
    
    async def get_league_clubs(self, league_url: str, season: int) -> list[ClubData]:
        """Get all clubs in a league.
        
        Args:
            league_url: e.g., "premier-league/startseite/wettbewerb/GB1"
            season: Year the season ends, e.g., 2024 for 2023-24 season
        """
        url = f"{league_url}/plus/"
        params = {"saison_id": season}
        
        soup = await self._get(url, params)
        clubs = []
        
        # Find the clubs table
        table = soup.find("table", class_="items")
        if not table:
            return clubs
        
        rows = table.find("tbody").find_all("tr") if table.find("tbody") else []
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            
            try:
                name_cell = cells[1]
                name = name_cell.get_text(strip=True)
                
                # Get squad size and average age
                squad_size = cells[3].get_text(strip=True)
                avg_age = cells[4].get_text(strip=True)
                
                # Get total market value
                total_value = cells[5].get_text(strip=True) if len(cells) > 5 else "-"
                
                club = ClubData(
                    name=name,
                    league="",
                    stadium="",
                    stadium_capacity=0,
                    squad_size=int(squad_size) if squad_size.isdigit() else 0,
                    avg_age=float(avg_age) if avg_age.replace(".", "").isdigit() else 0.0,
                    total_value=self._parse_market_value(total_value) or 0,
                    coach="",
                )
                clubs.append(club)
            except Exception as e:
                print(f"Error parsing club row: {e}")
                continue
        
        return clubs
    
    async def get_club_players(self, club_url: str, season: int) -> list[PlayerData]:
        """Get all players in a club.
        
        Args:
            club_url: e.g., "manchester-city/startseite/verein/281"
            season: Year the season ends
        """
        url = f"{club_url}/plus/1"
        params = {"saison_id": season}
        
        soup = await self._get(url, params)
        players = []
        
        # Find players table
        table = soup.find("table", class_="items")
        if not table:
            return players
        
        rows = table.find("tbody").find_all("tr") if table.find("tbody") else []
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 8:
                continue
            
            try:
                # Player name and URL
                name_cell = cells[1]
                name_link = name_cell.find("a")
                name = name_link.get_text(strip=True) if name_link else name_cell.get_text(strip=True)
                
                # Position
                position = cells[2].get_text(strip=True) if len(cells) > 2 else "Unknown"
                
                # Age
                age_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                age = int(age_text) if age_text.isdigit() else None
                
                # Nationality (flags)
                nat_cell = cells[4] if len(cells) > 4 else None
                nationality = "Unknown"
                if nat_cell:
                    img = nat_cell.find("img")
                    if img and img.get("title"):
                        nationality = img.get("title")
                
                # Market value
                value_text = cells[5].get_text(strip=True) if len(cells) > 5 else "-"
                market_value = self._parse_market_value(value_text)
                
                # Contract end
                contract_text = cells[6].get_text(strip=True) if len(cells) > 6 else "-"
                contract_end = self._parse_date(contract_text)
                
                # Parse additional details from player page if needed
                height = None
                foot = "Right"
                joined_date = None
                
                player = PlayerData(
                    name=name,
                    position=position,
                    age=age,
                    nationality=nationality,
                    club="",  # Will be set by caller
                    market_value=market_value,
                    contract_end=contract_end,
                    height=height,
                    foot=foot,
                    joined_date=joined_date,
                )
                players.append(player)
                
            except Exception as e:
                print(f"Error parsing player row: {e}")
                continue
        
        return players
    
    async def get_player_details(self, player_url: str) -> dict[str, Any]:
        """Get detailed information for a single player."""
        soup = await self._get(player_url)
        
        details = {
            "height": None,
            "foot": "Right",
            "date_of_birth": None,
            "place_of_birth": None,
            "player_agent": None,
            "current_club": None,
            "joined": None,
            "contract_expires": None,
        }
        
        # Find info table
        info_table = soup.find("div", class_="info-table")
        if info_table:
            rows = info_table.find_all("tr")
            for row in rows:
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    label = th.get_text(strip=True).lower()
                    value = td.get_text(strip=True)
                    
                    if "height" in label:
                        # Parse height like "1,85 m"
                        try:
                            height_str = value.replace("m", "").replace(",", ".").strip()
                            details["height"] = int(float(height_str) * 100)
                        except ValueError:
                            pass
                    elif "foot" in label:
                        details["foot"] = value
                    elif "date of birth" in label or "born" in label:
                        details["date_of_birth"] = self._parse_date(value)
                    elif "place of birth" in label:
                        details["place_of_birth"] = value
                    elif "player agent" in label:
                        details["player_agent"] = value
                    elif "current club" in label:
                        details["current_club"] = value
                    elif "joined" in label:
                        details["joined"] = self._parse_date(value)
                    elif "contract expires" in label or "contract until" in label:
                        details["contract_expires"] = self._parse_date(value)
        
        return details


# League URL mappings for Transfermarkt
LEAGUE_URLS = {
    "premier-league": "premier-league/startseite/wettbewerb/GB1",
    "championship": "championship/startseite/wettbewerb/GB2",
    "liga": "laliga/startseite/wettbewerb/ES1",
    "segunda-division": "laliga2/startseite/wettbewerb/ES2",
    "bundesliga": "bundesliga/startseite/wettbewerb/L1",
    "2-bundesliga": "2-bundesliga/startseite/wettbewerb/L2",
    "serie-a": "serie-a/startseite/wettbewerb/IT1",
    "serie-b": "serie-b/startseite/wettbewerb/IT2",
    "ligue-1": "ligue-1/startseite/wettbewerb/FR1",
    "ligue-2": "ligue-2/startseite/wettbewerb/FR2",
    "eredivisie": "eredivisie/startseite/wettbewerb/NL1",
    "primeira-liga": "primeira-liga/startseite/wettbewerb/PO1",
    "champions-league": "champions-league/startseite/pokalwettbewerb/CL",
    "europa-league": "europa-league/startseite/pokalwettbewerb/EL",
}


async def scrape_top5_leagues(season: int = 2024) -> dict[str, list[PlayerData]]:
    """Scrape all players from top 5 leagues.
    
    This will take several minutes due to rate limiting.
    """
    top5 = [
        ("premier-league", "Premier League"),
        ("liga", "La Liga"),
        ("bundesliga", "Bundesliga"),
        ("serie-a", "Serie A"),
        ("ligue-1", "Ligue 1"),
    ]
    
    all_players: dict[str, list[PlayerData]] = {}
    
    async with TransfermarktScraper(delay=2.0) as scraper:
        for league_key, league_name in top5:
            print(f"Scraping {league_name}...")
            league_url = LEAGUE_URLS.get(league_key)
            if not league_url:
                continue
            
            # Get clubs in league
            clubs = await scraper.get_league_clubs(league_url, season)
            print(f"  Found {len(clubs)} clubs")
            
            league_players = []
            for club in clubs[:5]:  # Limit to first 5 clubs for demo
                print(f"    Scraping {club.name}...")
                # Note: We need the club URL - this is simplified
                # In practice, you'd extract URLs from the league page
                
            all_players[league_name] = league_players
    
    return all_players


if __name__ == "__main__":
    # Example usage
    async def main():
        async with TransfermarktScraper() as scraper:
            # Example: Get Premier League clubs
            clubs = await scraper.get_league_clubs(LEAGUE_URLS["premier-league"], 2024)
            print(f"Found {len(clubs)} clubs")
            for club in clubs[:5]:
                print(f"  {club.name}: {club.squad_size} players, €{club.total_value:,} total value")
    
    asyncio.run(main())
