"""News System for FM Manager.

Generates dynamic news content:
- Match reports and results
- Transfer rumors and confirmed deals
- Club announcements
- Player interviews
- Manager comments
"""

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fm_manager.core.models import Match, Player, Club, TransferOffer


class NewsCategory(Enum):
    """Categories of news items."""
    MATCH_RESULT = "match_result"
    TRANSFER_RUMOR = "transfer_rumor"
    TRANSFER_CONFIRMED = "transfer_confirmed"
    INJURY = "injury"
    MANAGER_STATEMENT = "manager_statement"
    CLUB_ANNOUNCEMENT = "club_announcement"
    PLAYER_INTERVIEW = "player_interview"
    TACTICAL_ANALYSIS = "tactical_analysis"
    FINANCIAL = "financial"
    AWARD = "award"


class NewsPriority(Enum):
    """Priority levels for news items."""
    BREAKING = "breaking"      # Red banner, immediate notification
    HIGH = "high"              # Top of news feed
    MEDIUM = "medium"          # Standard placement
    LOW = "low"                # Bottom of feed


@dataclass
class NewsItem:
    """A single news item."""
    id: int = 0
    headline: str = ""
    content: str = ""
    summary: str = ""
    
    # Categorization
    category: NewsCategory = NewsCategory.CLUB_ANNOUNCEMENT
    priority: NewsPriority = NewsPriority.MEDIUM
    
    # Related entities
    club_id: int | None = None
    player_id: int | None = None
    match_id: int | None = None
    
    # Metadata
    date: date = field(default_factory=date.today)
    source: str = "Club Media"  # e.g., "BBC Sport", "Sky Sports", "Club Media"
    image_url: str | None = None
    
    # Engagement
    views: int = 0
    is_read: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "headline": self.headline,
            "content": self.content,
            "summary": self.summary,
            "category": self.category.value,
            "priority": self.priority.value,
            "club_id": self.club_id,
            "player_id": self.player_id,
            "match_id": self.match_id,
            "date": self.date.isoformat(),
            "source": self.source,
            "is_read": self.is_read,
        }


@dataclass
class NewsFeed:
    """Collection of news items for a user/club."""
    items: list[NewsItem] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add(self, item: NewsItem) -> None:
        """Add a news item to the feed."""
        item.id = len(self.items) + 1
        self.items.append(item)
        self.items.sort(key=lambda x: (x.date, x.priority.value), reverse=True)
        self.last_updated = datetime.now()
    
    def get_unread(self) -> list[NewsItem]:
        """Get all unread news items."""
        return [item for item in self.items if not item.is_read]
    
    def get_by_category(self, category: NewsCategory) -> list[NewsItem]:
        """Get news items by category."""
        return [item for item in self.items if item.category == category]
    
    def mark_all_read(self) -> None:
        """Mark all items as read."""
        for item in self.items:
            item.is_read = True
    
    def get_recent(self, days: int = 7) -> list[NewsItem]:
        """Get news from the last N days."""
        cutoff = date.today() - timedelta(days=days)
        return [item for item in self.items if item.date >= cutoff]


class NewsGenerator:
    """Generate news content."""
    
    # News sources
    SOURCES = [
        "BBC Sport",
        "Sky Sports",
        "ESPN FC",
        "Goal.com",
        "Transfermarkt",
        "Club Media",
        "The Guardian",
        "Football Insider",
    ]
    
    def __init__(self):
        self.next_id = 1
        self.templates = self._load_templates()
    
    def _load_templates(self) -> dict:
        """Load news templates."""
        return {
            "match_win": [
                "{team} Secure Victory Over {opponent}",
                "{team} Triumph in {opponent} Clash",
                "Three Points for {team} Against {opponent}",
            ],
            "match_loss": [
                "{team} Fall to {opponent} Defeat",
                "Disappointment for {team} Against {opponent}",
                "{team} Lose Out to {opponent}",
            ],
            "match_draw": [
                "{team} and {opponent} Share the Spoils",
                "Stalemate Between {team} and {opponent}",
                "Points Shared in {team} vs {opponent}",
            ],
            "transfer_rumor": [
                "{player} Linked with {club} Move",
                "{club} Interested in {player}",
                "{player} Rumored to Join {club}",
            ],
            "transfer_confirmed": [
                "{club} Sign {player}",
                "{player} Completes {club} Transfer",
                "{club} Announce {player} Signing",
            ],
            "injury": [
                "{player} Sidelined with Injury",
                "{club} Confirm {player} Injury",
                "Injury Blow for {player} and {club}",
            ],
            "manager_statement": [
                "{club} Manager: '{quote}'",
                "{club} Boss Speaks on {topic}",
                "{club} Manager Discusses {topic}",
            ],
        }
    
    def generate_match_news(
        self,
        match,
        home_club,
        away_club,
        key_player=None,
    ) -> NewsItem:
        """Generate news for a match result."""
        home_goals = match.home_score if hasattr(match, "home_score") else (match.home_goals if hasattr(match, "home_goals") else 0) or 0
        away_goals = match.away_score if hasattr(match, "away_score") else (match.away_goals if hasattr(match, "away_goals") else 0) or 0
        
        # Determine winner and template category
        if home_goals > away_goals:
            category = "match_win"
            main_team = home_club.name
            opponent = away_club.name
            winner_id = home_club.id
        elif away_goals > home_goals:
            category = "match_loss"
            main_team = home_club.name
            opponent = away_club.name
            winner_id = away_club.id
        else:
            category = "match_draw"
            main_team = home_club.name
            opponent = away_club.name
            winner_id = None
        
        headline = random.choice(self.templates[category]).format(
            team=main_team,
            opponent=opponent,
        )
        
        # Generate content
        content = self._generate_match_content(
            match, home_club, away_club, key_player
        )
        
        # Determine priority
        if home_club.reputation and away_club.reputation:
            if home_club.reputation > 8000 and away_club.reputation > 8000:
                priority = NewsPriority.HIGH
            else:
                priority = NewsPriority.MEDIUM
        else:
            priority = NewsPriority.MEDIUM
        
        return NewsItem(
            headline=headline,
            content=content,
            summary=self._generate_summary(content),
            category=NewsCategory.MATCH_RESULT,
            priority=priority,
            club_id=winner_id,
            match_id=match.id,
            date=match.match_date or date.today(),
            source=random.choice(self.SOURCES),
        )
    
    def _generate_match_content(self, match, home_club, away_club, key_player) -> str:
        """Generate detailed match content."""
        home_goals = match.home_score if hasattr(match, "home_score") else (match.home_goals if hasattr(match, "home_goals") else 0) or 0
        away_goals = match.away_score if hasattr(match, "away_score") else (match.away_goals if hasattr(match, "away_goals") else 0) or 0
        
        paragraphs = [
            f"{home_club.name} hosted {away_club.name} in a {home_goals}-{away_goals} encounter.",
        ]
        
        if home_goals > away_goals:
            paragraphs.append(
                f"The home side took all three points with a convincing performance."
            )
        elif away_goals > home_goals:
            paragraphs.append(
                f"The visitors came away with a valuable away victory."
            )
        else:
            paragraphs.append(
                f"Neither side could find a winner in a closely contested match."
            )
        
        if key_player:
            paragraphs.append(
                f"{key_player.full_name} was instrumental in the result."
            )
        
        return "\n\n".join(paragraphs)
    
    def generate_transfer_rumor(
        self,
        player,
        from_club,
        to_club,
        strength: str = "moderate",
    ) -> NewsItem:
        """Generate a transfer rumor news item."""
        headline = random.choice(self.templates["transfer_rumor"]).format(
            player=player.full_name,
            club=to_club.name,
        )
        
        content_templates = {
            "weak": [
                f"Reports suggest {to_club.name} may be monitoring {player.full_name}, "
                f"though any deal appears to be in early stages.",
            ],
            "moderate": [
                f"{to_club.name} are believed to be considering a move for {player.full_name}. "
                f"Sources indicate preliminary discussions have taken place.",
            ],
            "strong": [
                f"{player.full_name} is closing in on a move to {to_club.name}, "
                f"according to sources close to the player.",
            ],
        }
        
        content = random.choice(content_templates.get(strength, content_templates["moderate"]))
        
        priority_map = {
            "weak": NewsPriority.LOW,
            "moderate": NewsPriority.MEDIUM,
            "strong": NewsPriority.HIGH,
        }
        
        return NewsItem(
            headline=headline,
            content=content,
            summary=f"Transfer rumor: {player.full_name} to {to_club.name}",
            category=NewsCategory.TRANSFER_RUMOR,
            priority=priority_map.get(strength, NewsPriority.MEDIUM),
            club_id=to_club.id,
            player_id=player.id,
            source=random.choice(["Sky Sports", "ESPN FC", "Transfermarkt"]),
        )
    
    def generate_transfer_confirmed(
        self,
        player,
        from_club,
        to_club,
        fee: int,
    ) -> NewsItem:
        """Generate confirmed transfer news."""
        headline = random.choice(self.templates["transfer_confirmed"]).format(
            player=player.full_name,
            club=to_club.name,
        )
        
        fee_str = self._format_money(fee)
        
        content = (
            f"{to_club.name} have completed the signing of {player.full_name} from "
            f"{from_club.name} for a fee of {fee_str}.\n\n"
            f"The {player.position.value if player.position else 'player'} has signed a "
            f"contract with his new club and will join the squad immediately."
        )
        
        # Breaking news for big transfers
        if fee > 50_000_000 or (player.current_ability or 0) > 80:
            priority = NewsPriority.BREAKING
        elif fee > 20_000_000:
            priority = NewsPriority.HIGH
        else:
            priority = NewsPriority.MEDIUM
        
        return NewsItem(
            headline=headline,
            content=content,
            summary=f"{player.full_name} joins {to_club.name} for {fee_str}",
            category=NewsCategory.TRANSFER_CONFIRMED,
            priority=priority,
            club_id=to_club.id,
            player_id=player.id,
            source="Club Media",
        )
    
    def generate_injury_news(
        self,
        player,
        club,
        injury_type: str,
        duration_weeks: int,
    ) -> NewsItem:
        """Generate injury news."""
        headline = random.choice(self.templates["injury"]).format(
            player=player.full_name,
            club=club.name,
        )
        
        content = (
            f"{club.name} have confirmed that {player.full_name} will be sidelined "
            f"for approximately {duration_weeks} weeks with a {injury_type}.\n\n"
            f"The {player.position.value if player.position else 'player'} picked up "
            f"the injury during training and will undergo rehabilitation."
        )
        
        # Higher priority for key players
        priority = NewsPriority.HIGH if (player.current_ability or 0) > 75 else NewsPriority.MEDIUM
        
        return NewsItem(
            headline=headline,
            content=content,
            summary=f"{player.full_name} out for {duration_weeks} weeks",
            category=NewsCategory.INJURY,
            priority=priority,
            club_id=club.id,
            player_id=player.id,
            source="Club Media",
        )
    
    def generate_manager_statement(
        self,
        club,
        topic: str,
        quote: str,
    ) -> NewsItem:
        """Generate manager statement news."""
        headline = random.choice(self.templates["manager_statement"]).format(
            club=club.name,
            quote=quote[:50] + "..." if len(quote) > 50 else quote,
            topic=topic,
        )
        
        content = (
            f"The {club.name} manager has spoken about {topic}:\n\n"
            f'"{quote}"\n\n'
            f"These comments come as the club continues its campaign."
        )
        
        return NewsItem(
            headline=headline,
            content=content,
            summary=f"Manager speaks on {topic}",
            category=NewsCategory.MANAGER_STATEMENT,
            priority=NewsPriority.MEDIUM,
            club_id=club.id,
            source="Press Conference",
        )
    
    def generate_tactical_analysis(
        self,
        match,
        home_club,
        away_club,
    ) -> NewsItem:
        """Generate tactical analysis piece."""
        headline = f"Tactical Analysis: How {home_club.name} vs {away_club.name} Was Won"
        
        home_goals = match.home_score if hasattr(match, "home_score") else (match.home_goals if hasattr(match, "home_goals") else 0) or 0
        away_goals = match.away_score if hasattr(match, "away_score") else (match.away_goals if hasattr(match, "away_goals") else 0) or 0
        
        if home_goals > away_goals:
            winner, loser = home_club.name, away_club.name
            analysis = f"{winner}'s tactical approach proved superior"
        elif away_goals > home_goals:
            winner, loser = away_club.name, home_club.name
            analysis = f"{winner} executed their game plan effectively"
        else:
            winner = loser = None
            analysis = "Both sides cancelled each other out tactically"
        
        content = (
            f"Our tactical analysis of the {home_goals}-{away_goals} match between "
            f"{home_club.name} and {away_club.name}.\n\n"
            f"{analysis}. Key battles in midfield dictated the tempo, "
            f"while defensive organization played a crucial role in the outcome."
        )
        
        return NewsItem(
            headline=headline,
            content=content,
            summary=f"Tactical breakdown of {home_club.name} vs {away_club.name}",
            category=NewsCategory.TACTICAL_ANALYSIS,
            priority=NewsPriority.LOW,
            match_id=match.id,
            source="Football Insider",
        )
    
    def generate_award_news(
        self,
        player,
        award_name: str,
        month: str | None = None,
    ) -> NewsItem:
        """Generate player award news."""
        headline = f"{player.full_name} Wins {award_name}"
        
        time_period = f" for {month}" if month else ""
        
        content = (
            f"{player.full_name} has been named the {award_name}{time_period}.\n\n"
            f"The {player.position.value if player.position else 'player'} has been "
            f"in excellent form and fully deserves this recognition."
        )
        
        return NewsItem(
            headline=headline,
            content=content,
            summary=f"{player.full_name} claims {award_name}",
            category=NewsCategory.AWARD,
            priority=NewsPriority.HIGH,
            player_id=player.id,
            source="League Office",
        )
    
    def _generate_summary(self, content: str, max_length: int = 150) -> str:
        """Generate a brief summary of content."""
        if len(content) <= max_length:
            return content
        
        # Take first sentence or truncate
        sentences = content.split('.')
        if sentences:
            summary = sentences[0] + '.'
            if len(summary) > max_length:
                return content[:max_length-3] + "..."
            return summary
        
        return content[:max_length-3] + "..."
    
    def _format_money(self, amount: int) -> str:
        """Format money amount."""
        if amount >= 1_000_000_000:
            return f"€{amount/1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"€{amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"€{amount/1_000:.0f}K"
        return f"€{amount}"


class NewsSystem:
    """Main news system managing all news generation and feeds."""
    
    def __init__(self):
        self.generator = NewsGenerator()
        self.feeds: dict[int, NewsFeed] = {}  # club_id -> NewsFeed
        self.global_feed = NewsFeed()  # Global news for all clubs
    
    def get_or_create_feed(self, club_id: int) -> NewsFeed:
        """Get or create a news feed for a club."""
        if club_id not in self.feeds:
            self.feeds[club_id] = NewsFeed()
        return self.feeds[club_id]
    
    def add_match_result(
        self,
        match,
        home_club,
        away_club,
        key_player=None,
    ) -> NewsItem:
        """Add match result news to feeds."""
        news = self.generator.generate_match_news(match, home_club, away_club, key_player)
        
        # Add to global feed
        self.global_feed.add(news)
        
        # Add to club feeds
        if home_club.id:
            self.get_or_create_feed(home_club.id).add(news)
        if away_club.id:
            self.get_or_create_feed(away_club.id).add(news)
        
        return news
    
    def add_transfer_rumor(
        self,
        player,
        from_club,
        to_club,
        strength: str = "moderate",
    ) -> NewsItem:
        """Add transfer rumor to feeds."""
        news = self.generator.generate_transfer_rumor(
            player, from_club, to_club, strength
        )
        
        self.global_feed.add(news)
        
        if to_club.id:
            self.get_or_create_feed(to_club.id).add(news)
        
        return news
    
    def add_transfer_confirmed(
        self,
        player,
        from_club,
        to_club,
        fee: int,
    ) -> NewsItem:
        """Add confirmed transfer to feeds."""
        news = self.generator.generate_transfer_confirmed(
            player, from_club, to_club, fee
        )
        
        self.global_feed.add(news)
        
        if from_club.id:
            self.get_or_create_feed(from_club.id).add(news)
        if to_club.id:
            self.get_or_create_feed(to_club.id).add(news)
        
        return news
    
    def add_injury_news(
        self,
        player,
        club,
        injury_type: str,
        duration_weeks: int,
    ) -> NewsItem:
        """Add injury news to feed."""
        news = self.generator.generate_injury_news(
            player, club, injury_type, duration_weeks
        )
        
        if club.id:
            self.get_or_create_feed(club.id).add(news)
        
        return news
    
    def get_latest_news(
        self,
        club_id: int | None = None,
        count: int = 10,
    ) -> list[NewsItem]:
        """Get latest news items."""
        feed = self.global_feed if club_id is None else self.get_or_create_feed(club_id)
        return feed.items[:count]
    
    def get_breaking_news(self) -> list[NewsItem]:
        """Get all breaking news."""
        return [
            item for item in self.global_feed.items
            if item.priority == NewsPriority.BREAKING
        ]
    
    def generate_daily_news_digest(
        self,
        club_id: int,
        date: date,
    ) -> dict:
        """Generate a daily news digest for a club."""
        feed = self.get_or_create_feed(club_id)
        
        day_news = [item for item in feed.items if item.date == date]
        
        categories = {}
        for item in day_news:
            cat = item.category.value
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        return {
            "date": date.isoformat(),
            "total_items": len(day_news),
            "breaking": [item.to_dict() for item in day_news if item.priority == NewsPriority.BREAKING],
            "by_category": {
                cat: [item.to_dict() for item in items]
                for cat, items in categories.items()
            },
        }
