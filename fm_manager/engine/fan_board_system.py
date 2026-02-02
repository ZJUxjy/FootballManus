"""Fan and Board System for FM Manager.

Manages:
- Fan sentiment and reactions
- Board expectations and evaluations
- Manager job security
- Club atmosphere
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fm_manager.core.models import Club, Player, Match


class FanSentiment(Enum):
    """Fan sentiment levels."""
    ECSTATIC = "ecstatic"      # 90-100
    HAPPY = "happy"            # 75-89
    CONTENT = "content"        # 60-74
    NEUTRAL = "neutral"        # 45-59
    CONCERNED = "concerned"    # 30-44
    UNHAPPY = "unhappy"        # 15-29
    ANGRY = "angry"            # 0-14


class BoardConfidence(Enum):
    """Board confidence levels."""
    FULL = "full"              # Very secure
    HIGH = "high"              # Secure
    MODERATE = "moderate"      # Some pressure
    LOW = "low"                # Under pressure
    CRITICAL = "critical"      # On the brink


class ExpectationLevel(Enum):
    """Board expectation levels."""
    WIN_LEAGUE = "win_league"
    CHAMPIONS_LEAGUE = "champions_league"
    EUROPA_LEAGUE = "europa_league"
    TOP_HALF = "top_half"
    AVOID_RELEGATION = "avoid_relegation"


@dataclass
class FanOpinion:
    """Fan opinion on a specific topic."""
    topic: str  # e.g., "manager", "star_player", "transfer_policy"
    sentiment: int  # -100 to 100
    comments: list[str] = field(default_factory=list)
    
    def get_description(self) -> str:
        """Get text description of sentiment."""
        if self.sentiment > 75:
            return "Absolutely loved"
        elif self.sentiment > 50:
            return "Very popular"
        elif self.sentiment > 25:
            return "Well regarded"
        elif self.sentiment > -25:
            return "Mixed feelings"
        elif self.sentiment > -50:
            return "Unpopular"
        elif self.sentiment > -75:
            return "Very unpopular"
        else:
            return "Despised"


@dataclass
class BoardExpectations:
    """Board's expectations for the season."""
    club_id: int
    
    # Season targets
    league_position_target: int = 10
    cup_target: str = "reach_quarters"  # win/reach_final/reach_quarters
    european_target: str | None = None
    
    # Financial
    max_acceptable_loss: int = 50_000_000
    wage_bill_limit: int = 0  # 0 = no specific limit
    
    # Development
    youth_player_minutes_target: int = 5000  # Total minutes for U21 players
    
    # Style
    expected_playing_style: str = "attacking"  # attacking/balanced/defensive
    
    def to_dict(self) -> dict:
        return {
            "league_position": self.league_position_target,
            "cup": self.cup_target,
            "european": self.european_target,
            "financial_fair_play": True,
            "youth_development": self.youth_player_minutes_target,
        }


@dataclass
class ManagerEvaluation:
    """Board's evaluation of the manager."""
    club_id: int
    
    # Overall rating (0-100)
    overall_rating: int = 50
    
    # Specific areas
    tactical_rating: int = 50
    transfer_rating: int = 50
    man_management_rating: int = 50
    financial_rating: int = 50
    
    # Job security
    confidence: BoardConfidence = BoardConfidence.MODERATE
    weeks_under_pressure: int = 0
    
    # Board comments
    recent_feedback: list[str] = field(default_factory=list)
    
    def get_summary(self) -> str:
        """Get evaluation summary."""
        if self.overall_rating >= 80:
            return "Outstanding work"
        elif self.overall_rating >= 65:
            return "Good progress"
        elif self.overall_rating >= 50:
            return "Adequate"
        elif self.overall_rating >= 35:
            return "Needs improvement"
        else:
            return "Unsatisfactory"


@dataclass
class FanSentimentState:
    """Complete fan sentiment state."""
    club_id: int
    
    # Overall sentiment (0-100)
    overall_score: int = 50
    
    # Recent trend
    trend: str = "stable"  # rising/falling/stable
    trend_strength: int = 0  # How fast it's changing
    
    # Specific opinions
    opinions: dict[str, FanOpinion] = field(default_factory=dict)
    
    # Attendance impact
    attendance_modifier: float = 1.0  # 0.5-1.5 multiplier
    
    # Chants/songs
    popular_chants: list[str] = field(default_factory=list)
    
    def get_sentiment_level(self) -> FanSentiment:
        """Get current sentiment level."""
        score = self.overall_score
        if score >= 90:
            return FanSentiment.ECSTATIC
        elif score >= 75:
            return FanSentiment.HAPPY
        elif score >= 60:
            return FanSentiment.CONTENT
        elif score >= 45:
            return FanSentiment.NEUTRAL
        elif score >= 30:
            return FanSentiment.CONCERNED
        elif score >= 15:
            return FanSentiment.UNHAPPY
        else:
            return FanSentiment.ANGRY
    
    def get_description(self) -> str:
        """Get text description."""
        level = self.get_sentiment_level()
        descriptions = {
            FanSentiment.ECSTATIC: "Fans are absolutely delighted with how things are going!",
            FanSentiment.HAPPY: "Supporters are generally pleased with the club's direction.",
            FanSentiment.CONTENT: "Fans are satisfied but expect more.",
            FanSentiment.NEUTRAL: "Mixed feelings among the fanbase.",
            FanSentiment.CONCERNED: "Supporters are starting to worry.",
            FanSentiment.UNHAPPY: "Fans are vocal in their dissatisfaction.",
            FanSentiment.ANGRY: "The fans are furious and demanding changes!",
        }
        return descriptions[level]


class FanSystem:
    """Manages fan sentiment and reactions."""
    
    # Sentiment change factors
    WIN_BONUS = 8
    LOSS_PENALTY = -10
    DRAW_BONUS = 2
    
    # Modifier for match importance
    IMPORTANCE_MULTIPLIER = {
        "derby": 1.5,
        "title_race": 1.3,
        "relegation": 1.4,
        "cup_final": 1.5,
        "normal": 1.0,
    }
    
    def __init__(self):
        self.sentiments: dict[int, FanSentimentState] = {}  # club_id -> state
    
    def get_sentiment(self, club_id: int) -> FanSentimentState:
        """Get or create fan sentiment for a club."""
        if club_id not in self.sentiments:
            self.sentiments[club_id] = FanSentimentState(club_id=club_id)
        return self.sentiments[club_id]
    
    def update_after_match(
        self,
        club_id: int,
        won: bool,
        drawn: bool,
        importance: str = "normal",
    ) -> FanSentimentState:
        """Update fan sentiment after a match."""
        sentiment = self.get_sentiment(club_id)
        
        multiplier = self.IMPORTANCE_MULTIPLIER.get(importance, 1.0)
        
        if won:
            change = int(self.WIN_BONUS * multiplier)
            sentiment.trend = "rising"
        elif drawn:
            change = int(self.DRAW_BONUS * multiplier)
            sentiment.trend = "stable"
        else:
            change = int(self.LOSS_PENALTY * multiplier)
            sentiment.trend = "falling"
        
        sentiment.overall_score = max(0, min(100, sentiment.overall_score + change))
        sentiment.trend_strength = abs(change)
        
        # Update attendance modifier
        self._update_attendance_modifier(sentiment)
        
        return sentiment
    
    def _update_attendance_modifier(self, sentiment: FanSentimentState) -> None:
        """Update attendance based on sentiment."""
        score = sentiment.overall_score
        if score >= 80:
            sentiment.attendance_modifier = 1.1  # Sellouts likely
        elif score >= 60:
            sentiment.attendance_modifier = 1.0  # Normal
        elif score >= 40:
            sentiment.attendance_modifier = 0.9  # Slight drop
        elif score >= 20:
            sentiment.attendance_modifier = 0.75  # Noticeable drop
        else:
            sentiment.attendance_modifier = 0.6  # Boycotts possible
    
    def react_to_transfer(
        self,
        club_id: int,
        player_name: str,
        is_arrival: bool,
        fee: int = 0,
        player_quality: int = 50,
    ) -> str:
        """Generate fan reaction to a transfer."""
        sentiment = self.get_sentiment(club_id)
        
        if is_arrival:
            if player_quality > 75:
                reaction = f"Excellent signing! {player_name} is a real statement of intent."
                sentiment.overall_score = min(100, sentiment.overall_score + 5)
            elif player_quality > 60:
                reaction = f"Good addition. {player_name} should strengthen the squad."
                sentiment.overall_score = min(100, sentiment.overall_score + 2)
            elif fee > 30_000_000:
                reaction = f"Overpriced! {player_name} isn't worth that much."
                sentiment.overall_score = max(0, sentiment.overall_score - 3)
            else:
                reaction = f"Squad depth signing. Hope {player_name} works out."
        else:
            if player_quality > 75:
                reaction = f"Gutted to lose {player_name}. Big blow to our ambitions."
                sentiment.overall_score = max(0, sentiment.overall_score - 8)
            elif player_quality > 60:
                reaction = f"Shame to see {player_name} go, but maybe for the best."
                sentiment.overall_score = max(0, sentiment.overall_score - 3)
            else:
                reaction = f"Good riddance. {player_name} wasn't good enough."
                sentiment.overall_score = min(100, sentiment.overall_score + 1)
        
        return reaction
    
    def react_to_injury(
        self,
        club_id: int,
        player_name: str,
        duration_weeks: int,
        is_key_player: bool,
    ) -> str:
        """Generate fan reaction to an injury."""
        sentiment = self.get_sentiment(club_id)
        
        if is_key_player:
            if duration_weeks > 8:
                reaction = f"Devastating blow! We'll really miss {player_name}."
                sentiment.overall_score = max(0, sentiment.overall_score - 5)
            else:
                reaction = f"Concerned about {player_name}, but hopefully back soon."
                sentiment.overall_score = max(0, sentiment.overall_score - 2)
        else:
            reaction = f"Unfortunate for {player_name}, but squad should cope."
        
        return reaction
    
    def get_fan_chants(self, club_id: int) -> list[str]:
        """Get popular chants based on sentiment."""
        sentiment = self.get_sentiment(club_id)
        level = sentiment.get_sentiment_level()
        
        positive_chants = [
            "We're top of the league!",
            "Champions! Champions! Olé, Olé, Olé!",
            "The greatest team in football!",
            "We're gonna win the league!",
        ]
        
        neutral_chants = [
            "Come on you [team]!",
            "[Team] till I die!",
            "We love you [team], we do!",
        ]
        
        negative_chants = [
            "Sack the board!",
            "You're not fit to wear the shirt!",
            "We want our [team] back!",
            "This is embarrassing!",
        ]
        
        if level in [FanSentiment.ECSTATIC, FanSentiment.HAPPY]:
            return random.sample(positive_chants, min(3, len(positive_chants)))
        elif level in [FanSentiment.UNHAPPY, FanSentiment.ANGRY]:
            return random.sample(negative_chants, min(3, len(negative_chants)))
        else:
            return random.sample(neutral_chants, min(3, len(neutral_chants)))
    
    def get_social_media_reaction(self, club_id: int) -> list[dict]:
        """Generate social media style reactions."""
        sentiment = self.get_sentiment(club_id)
        level = sentiment.get_sentiment_level()
        
        reactions = {
            FanSentiment.ECSTATIC: [
                {"user": "@superfan", "text": "BEST TEAM IN THE WORLD!!! 🏆", "likes": 234},
                {"user": "@loyalsupporter", "text": "Proud to support this club! 💙", "likes": 189},
            ],
            FanSentiment.HAPPY: [
                {"user": "@matchgoer", "text": "Good result today! Onwards and upwards 📈", "likes": 145},
                {"user": "@season_ticket", "text": "Fully deserved 👏", "likes": 98},
            ],
            FanSentiment.CONCERNED: [
                {"user": "@worriedfan", "text": "Something needs to change... 😟", "likes": 67},
                {"user": "@analyst", "text": "Tactical issues are clear to see", "likes": 45},
            ],
            FanSentiment.ANGRY: [
                {"user": "@angryfan", "text": "EMBARRASSING! 😡", "likes": 456},
                {"user": "@time_to_go", "text": "Manager out! Board out!", "likes": 389},
                {"user": "@fed_up", "text": "Not spending another penny until things change", "likes": 234},
            ],
        }
        
        return reactions.get(level, [])


class BoardSystem:
    """Manages board expectations and evaluations."""
    
    def __init__(self):
        self.expectations: dict[int, BoardExpectations] = {}
        self.evaluations: dict[int, ManagerEvaluation] = {}
    
    def set_expectations(
        self,
        club,
        league_reputation: int = 5000,
        club_reputation: int | None = None,
    ) -> BoardExpectations:
        """Set board expectations based on club stature."""
        rep = club_reputation or club.reputation or 5000
        
        expectations = BoardExpectations(club_id=club.id or 0)
        
        # Set targets based on reputation
        if rep >= 9000:  # Elite
            expectations.league_position_target = 1
            expectations.cup_target = "win"
            expectations.european_target = "win_champions_league"
        elif rep >= 8000:  # Top 6
            expectations.league_position_target = 4
            expectations.cup_target = "reach_final"
            expectations.european_target = "reach_quarters"
        elif rep >= 7000:  # European contenders
            expectations.league_position_target = 6
            expectations.cup_target = "reach_quarters"
        elif rep >= 5000:  # Mid-table
            expectations.league_position_target = 10
            expectations.cup_target = "reach_quarters"
        elif rep >= 3000:  # Lower half
            expectations.league_position_target = 15
            expectations.cup_target = "reach_third_round"
        else:  # Relegation battlers
            expectations.league_position_target = 17
            expectations.cup_target = "reach_third_round"
        
        self.expectations[club.id or 0] = expectations
        return expectations
    
    def get_expectations(self, club_id: int) -> BoardExpectations | None:
        """Get board expectations for a club."""
        return self.expectations.get(club_id)
    
    def evaluate_manager(
        self,
        club_id: int,
        current_position: int,
        matches_played: int,
        wins: int,
        draws: int,
        losses: int,
        financial_fair_play: bool = True,
    ) -> ManagerEvaluation:
        """Evaluate manager performance."""
        evaluation = ManagerEvaluation(club_id=club_id)
        expectations = self.expectations.get(club_id)
        
        if not expectations:
            return evaluation
        
        # Calculate performance rating
        target = expectations.league_position_target
        position_diff = target - current_position  # Positive = exceeding
        
        # Base rating from position
        if position_diff >= 5:
            base_rating = 85  # Far exceeding
        elif position_diff >= 2:
            base_rating = 75  # Exceeding
        elif position_diff >= -2:
            base_rating = 60  # Meeting
        elif position_diff >= -5:
            base_rating = 45  # Below
        else:
            base_rating = 30  # Far below
        
        # Adjust for recent form (last 5 games)
        if matches_played >= 5:
            recent_points = (wins * 3 + draws)
            recent_max = min(5, matches_played) * 3
            form_ratio = recent_points / recent_max
            
            if form_ratio >= 0.8:
                base_rating += 10
            elif form_ratio >= 0.6:
                base_rating += 5
            elif form_ratio <= 0.2:
                base_rating -= 15
            elif form_ratio <= 0.4:
                base_rating -= 8
        
        # Financial penalty
        if not financial_fair_play:
            base_rating -= 10
        
        evaluation.overall_rating = max(0, min(100, base_rating))
        
        # Set confidence level
        if evaluation.overall_rating >= 80:
            evaluation.confidence = BoardConfidence.FULL
        elif evaluation.overall_rating >= 65:
            evaluation.confidence = BoardConfidence.HIGH
        elif evaluation.overall_rating >= 45:
            evaluation.confidence = BoardConfidence.MODERATE
        elif evaluation.overall_rating >= 30:
            evaluation.confidence = BoardConfidence.LOW
        else:
            evaluation.confidence = BoardConfidence.CRITICAL
        
        # Generate feedback
        evaluation.recent_feedback = self._generate_feedback(
            evaluation, expectations, current_position
        )
        
        self.evaluations[club_id] = evaluation
        return evaluation
    
    def _generate_feedback(
        self,
        evaluation: ManagerEvaluation,
        expectations: BoardExpectations,
        current_position: int,
    ) -> list[str]:
        """Generate board feedback."""
        feedback = []
        
        if evaluation.overall_rating >= 75:
            feedback.append("The board is delighted with your performance.")
            if current_position <= expectations.league_position_target:
                feedback.append(f"Exceeding our target position of {expectations.league_position_target}.")
        elif evaluation.overall_rating >= 55:
            feedback.append("The board is satisfied with progress.")
        elif evaluation.overall_rating >= 40:
            feedback.append("The board expects improvement.")
            if current_position > expectations.league_position_target:
                feedback.append(f"Currently below our target position of {expectations.league_position_target}.")
        else:
            feedback.append("The board is concerned about results.")
            feedback.append("Urgent improvement is required.")
        
        return feedback
    
    def check_job_security(self, club_id: int) -> dict:
        """Check manager's job security."""
        evaluation = self.evaluations.get(club_id)
        if not evaluation:
            return {"secure": True, "warning": False, "message": "No evaluation yet"}
        
        confidence = evaluation.confidence
        
        if confidence == BoardConfidence.CRITICAL:
            return {
                "secure": False,
                "warning": True,
                "message": "Your position is under serious threat. Two more defeats could see you sacked.",
                "matches_to_save_job": 2,
            }
        elif confidence == BoardConfidence.LOW:
            return {
                "secure": False,
                "warning": True,
                "message": "The board is losing patience. Improvement needed quickly.",
                "matches_to_save_job": 5,
            }
        elif confidence == BoardConfidence.MODERATE:
            return {
                "secure": True,
                "warning": False,
                "message": "Your position is relatively secure, but maintain progress.",
            }
        else:
            return {
                "secure": True,
                "warning": False,
                "message": "The board has full confidence in your leadership.",
            }
    
    def set_transfer_budget(
        self,
        club_id: int,
        finances,
        season_performance: str = "meeting",
    ) -> int:
        """Set transfer budget for next window."""
        base_budget = finances.balance * 0.2  # 20% of balance
        
        # Adjust based on performance
        multipliers = {
            "exceeding": 1.5,
            "meeting": 1.0,
            "below": 0.7,
            "crisis": 0.3,
        }
        
        multiplier = multipliers.get(season_performance, 1.0)
        budget = int(base_budget * multiplier)
        
        # Cap at reasonable limits
        return min(budget, 300_000_000)  # Max €300M


class FanBoardSystem:
    """Main system combining fan and board management."""
    
    def __init__(self):
        self.fan_system = FanSystem()
        self.board_system = BoardSystem()
    
    def process_match_result(
        self,
        club_id: int,
        won: bool,
        drawn: bool,
        importance: str = "normal",
        goals_for: int = 0,
        goals_against: int = 0,
    ) -> dict:
        """Process a match result for both fan and board systems."""
        # Update fan sentiment
        fan_sentiment = self.fan_system.update_after_match(
            club_id, won, drawn, importance
        )
        
        # Note: Board evaluation needs season context, updated separately
        
        return {
            "fan_sentiment": fan_sentiment.get_sentiment_level().value,
            "fan_description": fan_sentiment.get_description(),
            "attendance_modifier": fan_sentiment.attendance_modifier,
        }
    
    def get_club_atmosphere(self, club_id: int) -> dict:
        """Get overall club atmosphere."""
        fan_sentiment = self.fan_system.get_sentiment(club_id)
        board_eval = self.board_system.evaluations.get(club_id)
        
        # Calculate overall atmosphere
        fan_score = fan_sentiment.overall_score
        board_score = board_eval.overall_rating if board_eval else 50
        
        overall = (fan_score + board_score) / 2
        
        if overall >= 75:
            atmosphere = "Positive"
            description = "The club is in a great place both on and off the pitch."
        elif overall >= 50:
            atmosphere = "Stable"
            description = "Things are going reasonably well with room for improvement."
        elif overall >= 30:
            atmosphere = "Tense"
            description = "There are concerns that need to be addressed."
        else:
            atmosphere = "Crisis"
            description = "The club is in turmoil. Urgent action required."
        
        return {
            "overall_score": int(overall),
            "atmosphere": atmosphere,
            "description": description,
            "fan_sentiment": fan_sentiment.get_sentiment_level().value,
            "board_confidence": board_eval.confidence.value if board_eval else "unknown",
        }
    
    def generate_end_of_season_review(self, club_id: int) -> dict:
        """Generate end of season review."""
        fan_sentiment = self.fan_system.get_sentiment(club_id)
        board_eval = self.board_system.evaluations.get(club_id)
        expectations = self.board_system.get_expectations(club_id)
        
        review = {
            "fan_summary": "",
            "board_summary": "",
            "recommendations": [],
        }
        
        # Fan summary
        level = fan_sentiment.get_sentiment_level()
        if level in [FanSentiment.ECSTATIC, FanSentiment.HAPPY]:
            review["fan_summary"] = "Supporters have enjoyed a memorable season."
        elif level in [FanSentiment.CONCERNED, FanSentiment.UNHAPPY]:
            review["fan_summary"] = "Fans will look back on this season with disappointment."
        else:
            review["fan_summary"] = "A season of mixed emotions for the supporters."
        
        # Board summary
        if board_eval:
            if board_eval.overall_rating >= 75:
                review["board_summary"] = "The board is delighted with the season's achievements."
            elif board_eval.overall_rating >= 50:
                review["board_summary"] = "The board recognizes solid progress has been made."
            else:
                review["board_summary"] = "The board expects significant improvement next season."
        
        return review
