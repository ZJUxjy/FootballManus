"""Narrative Engine for FM Manager.

Generates AI-powered narratives for:
- Match events and summaries
- Player stories and personalities  
- Transfer rumors and news
- Season reviews
"""

import random
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from fm_manager.core.models import Match, Player, Club
from fm_manager.engine.match_engine_v2 import MatchEvent
from fm_manager.engine.llm_client import LLMClient, LLMProvider, FMPrompts


@dataclass
class MatchMoment:
    """A significant moment in a match for narrative generation."""
    minute: int
    event_type: str  # goal, red_card, penalty, substitution, etc.
    team: str
    player: str | None = None
    description: str = ""
    importance: float = 1.0  # 0-1, how significant
    
    def to_dict(self) -> dict:
        return {
            "minute": self.minute,
            "event_type": self.event_type,
            "team": self.team,
            "player": self.player,
            "description": self.description,
            "importance": self.importance,
        }


@dataclass
class PlayerStory:
    """A player's career story elements."""
    player_id: int
    personality_traits: list[str] = field(default_factory=list)
    career_highlights: list[str] = field(default_factory=list)
    media_narrative: str = ""
    fan_perception: str = "neutral"  # loved, liked, neutral, disliked, hated
    
    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "personality_traits": self.personality_traits,
            "career_highlights": self.career_highlights,
            "media_narrative": self.media_narrative,
            "fan_perception": self.fan_perception,
        }


@dataclass
class MatchNarrative:
    """Complete narrative for a match."""
    match_id: int
    headline: str = ""
    opening_paragraph: str = ""
    key_moments: list[dict] = field(default_factory=list)
    player_performances: list[dict] = field(default_factory=list)
    closing_paragraph: str = ""
    tone: str = "neutral"  # dramatic, neutral, analytical
    
    def to_full_report(self) -> str:
        """Generate full match report text."""
        lines = [
            f"# {self.headline}",
            "",
            self.opening_paragraph,
            "",
            "## Key Moments",
        ]
        
        for moment in self.key_moments:
            lines.append(f"\n**{moment['minute']}'** - {moment['description']}")
        
        if self.player_performances:
            lines.extend(["", "## Standout Performances"])
            for perf in self.player_performances:
                lines.append(f"- {perf['player']}: {perf['comment']}")
        
        lines.extend(["", self.closing_paragraph])
        
        return "\n".join(lines)


@dataclass
class SeasonStory:
    """Narrative for a club's season."""
    club_id: int
    season_year: int
    title: str = ""
    summary: str = ""
    key_matches: list[dict] = field(default_factory=list)
    player_stories: list[dict] = field(default_factory=list)
    turning_points: list[str] = field(default_factory=list)
    final_assessment: str = ""
    
    def to_dict(self) -> dict:
        return {
            "club_id": self.club_id,
            "season_year": self.season_year,
            "title": self.title,
            "summary": self.summary,
            "key_matches": self.key_matches,
            "player_stories": self.player_stories,
            "turning_points": self.turning_points,
            "final_assessment": self.final_assessment,
        }


class MatchNarrativeGenerator:
    """Generate match narratives using LLM."""
    
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient(provider=LLMProvider.MOCK)
    
    def generate_match_narrative(
        self,
        match: Match,
        events: list[MatchEvent],
        home_club: Club,
        away_club: Club,
        use_llm: bool = True,
    ) -> MatchNarrative:
        """Generate a complete narrative for a match."""
        # Extract key moments
        moments = self._extract_moments(events, home_club, away_club)
        
        # Generate headline
        headline = self._generate_headline(match, home_club, away_club)
        
        # Generate opening
        opening = self._generate_opening(match, home_club, away_club, moments)
        
        # Generate moment descriptions
        moment_narratives = []
        for moment in moments[:5]:  # Top 5 moments
            if use_llm:
                narrative = self._generate_moment_narrative_llm(moment, home_club, away_club)
            else:
                narrative = self._generate_moment_narrative_simple(moment)
            
            moment_narratives.append({
                "minute": moment.minute,
                "event_type": moment.event_type,
                "description": narrative,
            })
        
        # Generate closing
        closing = self._generate_closing(match, home_club, away_club)
        
        return MatchNarrative(
            match_id=match.id if match.id else 0,
            headline=headline,
            opening_paragraph=opening,
            key_moments=moment_narratives,
            closing_paragraph=closing,
            tone=self._determine_tone(match),
        )
    
    def _extract_moments(
        self,
        events: list[MatchEvent],
        home_club: Club,
        away_club: Club,
    ) -> list[MatchMoment]:
        """Extract significant moments from match events."""
        moments = []
        
        event_importance = {
            "goal": 1.0,
            "penalty_goal": 1.0,
            "own_goal": 0.9,
            "red_card": 0.8,
            "penalty_miss": 0.7,
            "yellow_card": 0.3,
            "substitution": 0.2,
        }
        
        for event in events:
            importance = event_importance.get(event.event_type, 0.1)
            
            # Adjust importance based on timing
            if event.minute and event.minute > 85 and importance > 0.5:
                importance = min(1.0, importance + 0.2)  # Late drama
            
            # Handle both team_id (int) and team (str "home"/"away") formats
            if hasattr(event, 'team_id') and event.team_id is not None:
                team_name = home_club.name if event.team_id == home_club.id else away_club.name
            elif hasattr(event, 'team'):
                team_name = home_club.name if event.team == "home" else away_club.name
            else:
                team_name = "Unknown"
            
            # Handle both event_type as string and as enum
            event_type_str = event.event_type
            if hasattr(event_type_str, 'value'):
                event_type_str = event_type_str.value
            
            # Handle player name
            player_name = None
            if hasattr(event, 'player_name'):
                player_name = event.player_name
            elif hasattr(event, 'player'):
                player_name = event.player
            
            moment = MatchMoment(
                minute=event.minute if hasattr(event, 'minute') and event.minute else 0,
                event_type=event_type_str,
                team=team_name,
                player=player_name,
                description=event.description if hasattr(event, 'description') else "",
                importance=importance,
            )
            moments.append(moment)
        
        # Sort by importance
        moments.sort(key=lambda m: m.importance, reverse=True)
        return moments
    
    def _generate_headline(self, match: Match, home: Club, away: Club) -> str:
        """Generate a match headline."""
        home_goals = match.home_score if hasattr(match, 'home_score') else (match.home_goals if hasattr(match, 'home_goals') else 0)
        away_goals = match.away_score if hasattr(match, 'away_score') else (match.away_goals if hasattr(match, 'away_goals') else 0)
        
        templates = {
            "close_win": [
                f"{home.name} Edge Past {away.name} in Tight Contest",
                f"Narrow Victory for {home.name} Against {away.name}",
                f"{home.name} Snatch Late Win Over {away.name}",
            ],
            "big_win": [
                f"{home.name} Dominate {away.name} in Emphatic Victory",
                f"{home.name} Run Riot Against {away.name}",
                f"{away.name} Crushed as {home.name} Fire on All Cylinders",
            ],
            "draw": [
                f"{home.name} and {away.name} Share the Spoils",
                f"Honors Even Between {home.name} and {away.name}",
                f"Stalemate at {home.name} as {away.name} Hold Firm",
            ],
            "upset": [
                f"Shock Result as {away.name} Stun {home.name}",
                f"{away.name} Pull Off Major Upset Against {home.name}",
                f"{home.name} Left Stunned by {away.name} Victory",
            ],
        }
        
        goal_diff = abs(home_goals - away_goals)
        
        if home_goals == away_goals:
            category = "draw"
        elif home_goals > away_goals:
            if goal_diff >= 3:
                category = "big_win"
            elif home.reputation and away.reputation and home.reputation < away.reputation - 2000:
                category = "upset"
            else:
                category = "close_win"
        else:
            if goal_diff >= 3:
                category = "upset"
            else:
                category = "close_win"
        
        return random.choice(templates[category])
    
    def _generate_opening(
        self,
        match: Match,
        home: Club,
        away: Club,
        moments: list[MatchMoment],
    ) -> str:
        """Generate opening paragraph."""
        home_goals = match.home_score if hasattr(match, 'home_score') else (match.home_goals if hasattr(match, 'home_goals') else 0)
        away_goals = match.away_score if hasattr(match, 'away_score') else (match.away_goals if hasattr(match, 'away_goals') else 0)
        
        templates = [
            f"{home.name} hosted {away.name} in a highly anticipated encounter that delivered on all fronts.",
            f"The match between {home.name} and {away.name} provided plenty of drama and excitement.",
            f"Fans were treated to an entertaining spectacle as {home.name} faced off against {away.name}.",
        ]
        
        opening = random.choice(templates)
        
        # Add result context
        if home_goals > away_goals:
            opening += f" In the end, the home side secured a {home_goals}-{away_goals} victory."
        elif away_goals > home_goals:
            opening += f" The visitors came away with a surprising {away_goals}-{home_goals} win."
        else:
            opening += f" Neither side could find a winner, with the match ending {home_goals}-{away_goals}."
        
        return opening
    
    def _generate_moment_narrative_llm(
        self,
        moment: MatchMoment,
        home: Club,
        away: Club,
    ) -> str:
        """Generate narrative for a moment using LLM."""
        try:
            prompt = FMPrompts.MATCH_NARRATIVE.format(
                home_team=home.name,
                away_team=away.name,
                minute=moment.minute,
                event_type=moment.event_type.replace("_", " ").title(),
                details=moment.description or f"{moment.player} involved",
            )
            
            response = self.llm.generate(
                prompt,
                max_tokens=150,
                temperature=0.8,
            )
            
            return response.content.strip()
        except Exception:
            return self._generate_moment_narrative_simple(moment)
    
    def _generate_moment_narrative_simple(self, moment: MatchMoment) -> str:
        """Generate simple narrative without LLM."""
        templates = {
            "goal": [
                f"A fantastic strike from {moment.player} gave {moment.team} the lead.",
                f"{moment.player} found the back of the net with a well-taken goal.",
                f"The breakthrough came through {moment.player} who finished clinically.",
            ],
            "penalty_goal": [
                f"{moment.player} kept his cool to convert from the spot.",
                f"The penalty was dispatched confidently by {moment.player}.",
            ],
            "red_card": [
                f"The referee showed red to {moment.player}, reducing {moment.team} to ten men.",
                f"A costly dismissal for {moment.player} left {moment.team} in trouble.",
            ],
            "own_goal": [
                f"An unfortunate own goal handed the advantage to the opposition.",
                f"The defender's attempted clearance ended up in his own net.",
            ],
        }
        
        event_templates = templates.get(moment.event_type, ["A key moment in the match."])
        return random.choice(event_templates)
    
    def _generate_closing(self, match: Match, home: Club, away: Club) -> str:
        """Generate closing paragraph."""
        home_goals = match.home_score if hasattr(match, 'home_score') else (match.home_goals if hasattr(match, 'home_goals') else 0)
        away_goals = match.away_score if hasattr(match, 'away_score') else (match.away_goals if hasattr(match, 'away_goals') else 0)
        
        if home_goals > away_goals:
            templates = [
                f"{home.name} will be pleased with this result as they look to build momentum.",
                f"A valuable three points for {home.name} in their campaign.",
                f"The victory keeps {home.name}'s hopes alive in the race for silverware.",
            ]
        elif away_goals > home_goals:
            templates = [
                f"{away.name} will celebrate this impressive away victory.",
                f"A statement win for {away.name} on the road.",
                f"{home.name} will need to regroup after this disappointing home defeat.",
            ]
        else:
            templates = [
                f"Both teams will feel they could have taken more from this encounter.",
                f"A point apiece, but both {home.name} and {away.name} may feel frustrated.",
                f"The draw does little to help either side's ambitions.",
            ]
        
        return random.choice(templates)
    
    def _determine_tone(self, match: Match) -> str:
        """Determine narrative tone based on match characteristics."""
        home_goals = match.home_score if hasattr(match, 'home_score') else (match.home_goals if hasattr(match, 'home_goals') else 0)
        away_goals = match.away_score if hasattr(match, 'away_score') else (match.away_goals if hasattr(match, 'away_goals') else 0)
        total_goals = home_goals + away_goals
        
        if total_goals >= 5:
            return "dramatic"
        elif total_goals <= 1:
            return "analytical"
        else:
            return "neutral"


class PlayerNarrativeGenerator:
    """Generate player stories and personalities."""
    
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient(provider=LLMProvider.MOCK)
    
    def generate_player_story(self, player: Player, use_llm: bool = True) -> PlayerStory:
        """Generate a narrative profile for a player."""
        story = PlayerStory(player_id=player.id or 0)
        
        # Generate personality traits
        story.personality_traits = self._generate_personality_traits(player)
        
        # Generate career highlights
        story.career_highlights = self._generate_career_highlights(player)
        
        # Generate media narrative
        if use_llm:
            story.media_narrative = self._generate_media_narrative_llm(player)
        else:
            story.media_narrative = self._generate_media_narrative_simple(player)
        
        # Determine fan perception
        story.fan_perception = self._determine_fan_perception(player)
        
        return story
    
    def _generate_personality_traits(self, player: Player) -> list[str]:
        """Generate personality traits based on attributes."""
        traits = []
        
        # Based on mental attributes
        if (getattr(player, 'determination', 50) or 50) > 70:
            traits.append("highly determined")
        if (getattr(player, 'leadership', 50) or 50) > 70:
            traits.append("natural leader")
        if (getattr(player, 'work_rate', 50) or 50) > 70:
            traits.append("hard worker")
        if (getattr(player, 'flair', 50) or 50) > 70:
            traits.append("flamboyant")
        if (getattr(player, 'aggression', 50) or 50) > 70:
            traits.append("combative")
        if (getattr(player, 'teamwork', 50) or 50) > 70:
            traits.append("team player")
        
        # Default traits if few detected
        if len(traits) < 2:
            default_traits = ["professional", "consistent", "reliable", "ambitious"]
            traits.extend(random.sample(default_traits, 3 - len(traits)))
        
        return traits
    
    def _generate_career_highlights(self, player: Player) -> list[str]:
        """Generate career highlights based on player stats."""
        highlights = []
        
        age = player.age or 25
        ca = player.current_ability or 50
        
        if ca > 85:
            highlights.append("Considered one of the best in his position")
        if ca > 75:
            highlights.append("Regular starter at top level")
        if age < 22 and (player.potential_ability or 50) > 80:
            highlights.append("Hot prospect with bright future")
        if age > 30 and ca > 70:
            highlights.append("Veteran with wealth of experience")
        
        if not highlights:
            highlights.append("Solid professional making steady progress")
        
        return highlights
    
    def _generate_media_narrative_llm(self, player: Player) -> str:
        """Generate media narrative using LLM."""
        try:
            # Build attributes string
            attrs = []
            if hasattr(player, 'pace') and player.pace:
                attrs.append(f"pace {player.pace}")
            if hasattr(player, 'shooting') and player.shooting:
                attrs.append(f"shooting {player.shooting}")
            if hasattr(player, 'passing') and player.passing:
                attrs.append(f"passing {player.passing}")
            
            prompt = FMPrompts.PLAYER_PROFILE.format(
                player_name=player.full_name,
                position=player.position.value if player.position else "Unknown",
                age=player.age or 25,
                attributes=", ".join(attrs) if attrs else "well-rounded",
            )
            
            response = self.llm.generate(prompt, max_tokens=200)
            return response.content.strip()
        except Exception:
            return self._generate_media_narrative_simple(player)
    
    def _generate_media_narrative_simple(self, player: Player) -> str:
        """Generate simple media narrative."""
        templates = [
            f"{player.full_name} is a {player.position.value if player.position else 'versatile'} player known for his technical ability.",
            f"A reliable presence in the squad, {player.full_name} consistently delivers solid performances.",
            f"At {player.age or 25}, {player.full_name} is in the prime of his career and showing no signs of slowing down.",
        ]
        return random.choice(templates)
    
    def _determine_fan_perception(self, player: Player) -> str:
        """Determine how fans perceive the player."""
        ca = player.current_ability or 50
        
        if ca > 80:
            return "loved"
        elif ca > 65:
            return "liked"
        elif ca > 50:
            return "neutral"
        else:
            return "disliked"


class SeasonNarrativeGenerator:
    """Generate season-long narratives."""
    
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient(provider=LLMProvider.MOCK)
    
    def generate_season_story(
        self,
        club: Club,
        season_year: int,
        final_position: int,
        key_matches: list[Match],
        top_scorer: Player | None = None,
        use_llm: bool = True,
    ) -> SeasonStory:
        """Generate a season story for a club."""
        story = SeasonStory(
            club_id=club.id or 0,
            season_year=season_year,
        )
        
        # Generate title
        story.title = self._generate_season_title(club, final_position)
        
        # Generate summary
        if use_llm:
            story.summary = self._generate_summary_llm(club, final_position, top_scorer)
        else:
            story.summary = self._generate_summary_simple(club, final_position)
        
        # Extract key matches
        story.key_matches = self._process_key_matches(key_matches)
        
        # Generate turning points
        story.turning_points = self._generate_turning_points(final_position)
        
        # Final assessment
        story.final_assessment = self._generate_assessment(club, final_position)
        
        return story
    
    def _generate_season_title(self, club: Club, position: int) -> str:
        """Generate a season title."""
        if position == 1:
            return f"{club.name}: Champions!"
        elif position <= 4:
            return f"{club.name}: Top Four Finish"
        elif position <= 7:
            return f"{club.name}: European Qualification Secured"
        elif position <= 10:
            return f"{club.name}: Solid Mid-Table Campaign"
        elif position <= 17:
            return f"{club.name}: Survival Battle"
        else:
            return f"{club.name}: Relegation Heartbreak"
    
    def _generate_summary_llm(
        self,
        club: Club,
        position: int,
        top_scorer: Player | None,
    ) -> str:
        """Generate season summary using LLM."""
        try:
            achievements = []
            if position == 1:
                achievements.append("League Champions")
            elif position <= 4:
                achievements.append("Champions League Qualification")
            elif position <= 6:
                achievements.append("European Competition Qualification")
            
            notable = []
            if top_scorer:
                notable.append(f"{top_scorer.full_name} leading the attack")
            
            prompt = FMPrompts.SEASON_REVIEW.format(
                club_name=club.name,
                position=f"{position}{self._ordinal(position)}",
                achievements=", ".join(achievements) if achievements else "Mid-table finish",
                notable_players=", ".join(notable) if notable else "squad contributions",
            )
            
            response = self.llm.generate(prompt, max_tokens=300)
            return response.content.strip()
        except Exception:
            return self._generate_summary_simple(club, position)
    
    def _generate_summary_simple(self, club: Club, position: int) -> str:
        """Generate simple season summary."""
        if position == 1:
            return f"A magnificent season for {club.name} as they claimed the title."
        elif position <= 4:
            return f"{club.name} secured a top-four finish, ensuring European football next season."
        elif position <= 10:
            return f"A respectable mid-table finish for {club.name} in a competitive campaign."
        elif position <= 17:
            return f"{club.name} battled hard to maintain their top-flight status."
        else:
            return f"A disappointing season ended in relegation for {club.name}."
    
    def _process_key_matches(self, matches: list[Match]) -> list[dict]:
        """Process key matches for the narrative."""
        processed = []
        
        for match in matches[:5]:  # Top 5 matches
            home_goals = match.home_score if hasattr(match, 'home_score') else (match.home_goals if hasattr(match, 'home_goals') else 0)
            away_goals = match.away_score if hasattr(match, 'away_score') else (match.away_goals if hasattr(match, 'away_goals') else 0)
            processed.append({
                "opponent": getattr(match, 'opponent_name', 'Unknown'),
                "result": f"{home_goals}-{away_goals}",
                "significance": self._classify_match_importance(match),
            })
        
        return processed
    
    def _classify_match_importance(self, match: Match) -> str:
        """Classify how important a match was."""
        home_goals = match.home_score if hasattr(match, 'home_score') else (match.home_goals if hasattr(match, 'home_goals') else 0)
        away_goals = match.away_score if hasattr(match, 'away_score') else (match.away_goals if hasattr(match, 'away_goals') else 0)
        total_goals = home_goals + away_goals
        
        if total_goals >= 5:
            return "thriller"
        elif total_goals == 0:
            return "hard-fought"
        else:
            return "crucial"
    
    def _generate_turning_points(self, position: int) -> list[str]:
        """Generate season turning points."""
        if position <= 4:
            return [
                "Strong start to the season set the tone",
                "Key victories against direct rivals proved decisive",
                "Squad depth helped maintain consistency",
            ]
        elif position <= 10:
            return [
                "Inconsistent form plagued mid-season",
                "Improved finish salvaged respectability",
            ]
        else:
            return [
                "Poor start left playing catch-up",
                "Management changes brought mixed results",
                "Late rally wasn't enough to avoid the drop",
            ]
    
    def _generate_assessment(self, club: Club, position: int) -> str:
        """Generate final assessment."""
        if position == 1:
            return f"Champions. A season to remember for {club.name} fans."
        elif position <= 4:
            return f"Successful campaign. The foundation is set for future challenges."
        elif position <= 10:
            return f"Adequate season, but room for improvement remains."
        else:
            return f"Relegation is a setback, but {club.name} has the resources to bounce back."
    
    def _ordinal(self, n: int) -> str:
        """Get ordinal suffix for number."""
        if 11 <= n % 100 <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


class NarrativeEngine:
    """Main narrative engine combining all generators."""
    
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient(provider=LLMProvider.MOCK)
        self.match_gen = MatchNarrativeGenerator(self.llm)
        self.player_gen = PlayerNarrativeGenerator(self.llm)
        self.season_gen = SeasonNarrativeGenerator(self.llm)
    
    def generate_match_report(
        self,
        match: Match,
        events: list[MatchEvent],
        home_club: Club,
        away_club: Club,
        use_llm: bool = False,
    ) -> MatchNarrative:
        """Generate a complete match report."""
        return self.match_gen.generate_match_narrative(
            match, events, home_club, away_club, use_llm
        )
    
    def generate_player_profile(
        self,
        player: Player,
        use_llm: bool = False,
    ) -> PlayerStory:
        """Generate a player profile."""
        return self.player_gen.generate_player_story(player, use_llm)
    
    def generate_season_review(
        self,
        club: Club,
        season_year: int,
        final_position: int,
        key_matches: list[Match],
        top_scorer: Player | None = None,
        use_llm: bool = False,
    ) -> SeasonStory:
        """Generate a season review."""
        return self.season_gen.generate_season_story(
            club, season_year, final_position, key_matches, top_scorer, use_llm
        )
