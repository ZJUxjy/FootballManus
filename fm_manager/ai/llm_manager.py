"""LLM-Powered Football Manager.

An AI manager that uses LLM to make intelligent decisions about:
- Squad management and lineups
- Tactical formations and in-match adjustments
- Transfer targets and negotiations
- Financial decisions within budget constraints
- Club development and objectives
- Press conferences and player interactions
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum, auto
from typing import Optional, Dict, List, Any, Callable
from pydantic import BaseModel, Field

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fm_manager.core.models import (
    Club, Player, Match, League, Transfer,
    TransferStatus, ContractOffer
)
from fm_manager.core.database import get_db_session
from fm_manager.engine.team_state import TeamStateManager, PlayerMatchState
from fm_manager.engine.match_engine_markov_v2 import (
    EnhancedMarkovEngine, TacticalFormation, MatchStage
)
from fm_manager.engine.transfer_engine_enhanced import EnhancedTransferEngine, TransferNegotiation
from fm_manager.engine.finance_engine import FinanceEngine


class ManagerStyle(Enum):
    """Manager personality and tactical style."""
    POSSESSION = "possession"     # Keep ball, short passes
    COUNTER_ATTACK = "counter"    # Direct attacks, fast breaks
    HIGH_PRESS = "pressing"      # Press high up the pitch
    LOW_BLOCK = "low_block"       # Defend deep, counter
    TIKI_TAKA = "tiki_taka"    # Short passes, retain possession
    ROUT_ONE = "route_one"       # Long balls to targets
    GEGENPRESSING = "gegenpressing" # Aggressive pressing
    PARK_BUS = "park_bus"        # Park the bus


class ManagerPersonality(Enum):
    """Manager personality affecting decision making."""
    PRAGMATIC = "pragmatic"
    AMBITIOUS = "ambitious"
    ATTACKING = "attacking"
    DEFENSIVE = "defensive"
    YOUTH_FOCUS = "youth_focus"  # Prioritizes young players
    VETERAN = "veteran"  # Trusts experienced players
    ROMANTIC = "romantic" # Plays attractive football
    MERCENARY = "mercenary"   # Will buy/sell for profit


class TacticalDecision(Enum):
    """Tactical decision types."""
    FORMATION = "formation"
    STYLE_CHANGE = "style_change"
    SUBSTITUTION = "substitution"
    TIMING = "timing"
    INTENSITY = "intensity"


class TransferDecision(Enum):
    """Transfer-related decisions."""
    IDENTIFY_TARGET = "identify_target"
    MAKE_OFFER = "make_offer"
    ACCEPT_OFFER = "accept_offer"
    REJECT_OFFER = "reject_offer"
    SELL_PLAYER = "sell_player"
    CONTRACT_NEGOTIATION = "contract_negotiation"
    LIST_PLAYER = "list_player"
    LOAN_DECISION = "loan_decision"


@dataclass
class ClubContext:
    """All relevant context about the club for LLM decisions."""
    club_id: int
    club_name: str
    reputation: int

    # Financial
    balance: int
    transfer_budget: int
    wage_budget: int
    ffp_status: str

    # Objectives
    season_objective: str  # "top_4", "top_8", "avoid_relegation", etc.
    board_confidence: int  # 0-100

    # Squad
    squad_size: int
    average_age: float
    star_players: List[str]

    # League context
    league_position: int
    league_points: int
    form: List[str]  # Last 5 results

    # Tactical identity
    preferred_style: ManagerStyle = ManagerStyle.BALANCED
    preferred_formation: str = "4-3-3"

    # Recent results
    last_match_date: Optional[date] = None
    last_opponent: Optional[str] = None
    last_result: str = "N/A"

    # Opposition
    next_opponent: Optional[str] = None
    next_venue: Optional[str] = None


@dataclass
class PlayerEvaluation:
    """AI's evaluation of a player."""
    player_id: int
    player_name: str
    position: str

    # Ability ratings
    current_ability: int
    potential_ability: int
    form: int 0-100

    # Tactical fit
    positional_fit: str  # "perfect", "good", "acceptable", "poor"
    team_fit: int = 50  # How well they fit the system

    # Role
    squad_role: str  # "starter", "rotation", "prospect", "deadwood"

    # Value
    market_value: int
    importance: str  # "star", "key", "squad", "squad_player"

    # Contract situation
    contract_status: str  # "secure", "expiring_soon", "available"
    years_remaining: int

    # Interest level
    selling_interest: bool = False


@dataclass
class TacticalPlan:
    """Tactical plan for upcoming match."""
    formation: str  # e.g., "4-3-3", "4-2-3-1"
    style: ManagerStyle = ManagerStyle.BALANCED
    mentality: str = "balanced"  # "attacking", "balanced", "defensive"
    pressing_intensity: str = "medium"  # "low", "medium", "high"

    # Key instructions
    focus_area: str = "balanced"  # "left", "right", "central", "wide"
    risk_level: str = "controlled"  # "cautious", "normal", "aggressive"

    # Player selection notes
    unavailable_players: List[int] = field(default_factory=list)
    tactical_changes: List[str] = field(default_factory=list)


@dataclass
class TransferStrategy:
    """Transfer strategy for the transfer window."""
    budget_allocation: Dict[str, int] = field(default_factory=lambda: {
        "attack": 50,
        "midfield": 30,
        "defense": 10,
        "goalkeeper": 10,
    })

    # Priority positions based on squad needs
    priority_positions: List[str] = field(default_factory=list)

    # Age profile preferences
    min_age: int = 18
    max_age: int = 32

    # Budget strategy
    max_single_fee: int = 0  # Will be calculated
    max_total_spend: int = 0

    # Loan preferences
    open_to_loans: bool = True
    prefer_buy_option: bool = False

    # Selling policy
    sell_deadwood: bool = True
    sell_clauses: bool = False  # Only when needed

    # Timeline
    early_window_targets: int = 0  # Targets to complete early
    deadline_day_moves: List[int] = []  # Which days to push harder for deals


@dataclass
class ManagerDecision:
    """A decision made by the AI manager."""
    timestamp: date
    decision_type: str
    category: str  # "tactical", "transfer", "squad", "financial"
    reasoning: str

    # Decision details
    details: Dict[str, Any] = field(default_factory=dict)

    # Confidence level (0-100)
    confidence: int = 75

    # Execution status
    status: str = "pending"  # "pending", "approved", "rejected", "completed", "cancelled"


class LLMManager:
    """AI-powered football manager using LLM for decision making."""

    def __init__(
        self,
        club_id: int,
        personality: ManagerPersonality = ManagerPersonality.BALANCED,
        llm_provider: str = "openai",
        model_name: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        self.club_id = club_id
        self.personality = personality
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.api_key = api_key
        self.database_url = database_url

        # State tracking
        self.transfer_strategy = TransferStrategy()
        self.current_tactical_plan: Optional[TacticalPlan] = None
        self.player_evaluations: Dict[int, PlayerEvaluation] = {}

        # Decision history
        self.decisions: List[ManagerDecision] = []

        # Statistics
        self.matches_managed: int = 0
        self.wins: int = 0
        self.draws: int = 0
        self.transfers_completed: int = 0

    async def get_club_context(self, session: AsyncSession) -> ClubContext:
        """Get comprehensive club context for LLM decisions."""
        # Get club
        club = await session.get(Club, self.club_id)
        if not club:
            raise ValueError(f"Club {self.club_id} not found")

        # Get league
        league = await session.get(League, club.league_id)
        league_position = 0
        if league:
            # Would need to calculate from standings
            pass

        # Get squad
        from sqlalchemy import func
        result = await session.execute(
            select(Player)
            .where(Player.club_id == self.club_id)
        )
        players = list(result.scalars().all())

        if not players:
            raise ValueError(f"No players found for club {club.name}")

        # Calculate squad metrics
        total_players = len(players)
        total_age = sum(p.age or 25 for p in players)
        avg_age = total_age / total_players if total_players > 0 else 25

        total_ability = sum(p.current_ability or 50 for p in players)
        avg_ability = total_ability / total_players if total_players > 0 else 50

        # Get star players (top 5 by ability)
        sorted_players = sorted(
            [(p, p.current_ability or 50) for p in players],
            key=lambda x: x[1],
            reverse=True
        )
        star_players = [p[0].full_name for p, _ in sorted_players[:5]]

        # Identify position needs
        position_counts = {}
        for p in players:
            pos = p.position.value if p.position else "MID"
            position_counts[pos] = position_counts.get(pos, 0) + 1

        # Find weakest positions
        weak_positions = []
        for pos, count in position_counts.items():
            if count < 2:  # Need at least 2 players per position
                weak_positions.append(pos)

        # Get form (would come from match results)
        form = ["W", "W", "D", "D", "L"]  # Placeholder

        return ClubContext(
            club_id=club.id,
            club_name=club.name or "Unknown",
            reputation=club.reputation or 5000,
            balance=club.balance or 0,
            transfer_budget=club.transfer_budget or 50_000_000,
            wage_budget=club.wage_budget or 5_000_000,
            ffp_status="compliant",
            season_objective="mid_table",
            board_confidence=75,
            squad_size=total_players,
            average_age=avg_age,
            star_players=star_players,
            league_position=league_position,
            league_points=0,
            form=form,
            preferred_style=self._map_personality_to_style(),
            preferred_formation="4-3-3",
            last_match_date=None,
            last_opponent=None,
            last_result="N/A",
            next_opponent=None,
            next_venue=None,
        )

    def _map_personality_to_style(self) -> ManagerStyle:
        """Map personality to preferred playing style."""
        style_map = {
            ManagerStyle.POSSESSION: ManagerStyle.POSSESSION,
            ManagerStyle.TIKI_TAKA: ManagerStyle.TIKI_TAKA,
            ManagerStyle.ROUT_ONE: ManagerStyle.ROUT_ONE,
        }
        return style_map.get(self.personality, ManagerStyle.BALANCED)

    async def evaluate_players(self, session: AsyncSession) -> Dict[int, PlayerEvaluation]:
        """Evaluate all players in the squad."""
        context = await self.get_club_context(session)

        evaluations = {}

        for player in context.squad_players:
            # Get player attributes
            ca = player.current_ability or 50
            potential = player.potential_ability or 50

            # Calculate positional fit (simplified)
            pos = player.position.value if player.position else "MID"
            fit_score = min(100, ca + (potential - ca) // 2)

            if fit_score > 85:
                positional_fit = "perfect"
            elif fit_score > 75:
                positional_fit = "good"
            elif fit_score > 65:
                positional_fit = "acceptable"
            else:
                positional_fit = "poor"

            # Determine squad role
            if ca > 80 and positional_fit in ["perfect", "good"]:
                squad_role = "starter"
            elif ca > 70 and context.club_reputation > 6000:
                squad_role = "key_player"
            elif ca > 60:
                squad_role = "rotation"
            elif ca < 22 or player.age < 20:
                squad_role = "prospect"
            else:
                squad_role = "deadwood"

            # Calculate team fit
            # Consider positional needs
            team_fit = fit_score
            if player.age < 23:
                team_fit += 5  # Youth bonus

            # Determine importance
            if ca > 80:
                importance = "star"
            elif ca > 70:
                importance = "key"
            elif ca > 60:
                importance = "squad"
            elif squad_role in ["starter", "key_player"]:
                importance = "squad_player"
            else:
                importance = "squad_player"

            # Contract status
            contract_status = "secure"
            if player.contract_until:
                days_left = (player.contract_until - date.today()).days
                if days_left < 90:
                    contract_status = "expiring_soon"
                elif days_left < 365:
                    contract_status = "available"
                else:
                    contract_status = "expiring_soon"

            # Market value
            market_value = ca * 150_000  # Simplified

            evaluations[player.id] = PlayerEvaluation(
                player_id=player.id or 0,
                player_name=player.full_name or "Unknown",
                position=pos,
                current_ability=ca,
                potential_ability=potential,
                form=50,
                positional_fit=positional_fit,
                team_fit=team_fit,
                squad_role=squad_role,
                market_value=market_value,
                importance=importance,
                contract_status=contract_status,
                years_remaining=2,
            )

        return evaluations

    async def plan_lineup(
        self,
        opponent_id: int,
        match_importance: str = "normal",
        available_players: List[int],
        session: AsyncSession,
    ) -> TacticalPlan:
        """Plan tactics and lineup for upcoming match."""
        # Get club context
        context = await self.get_club_context(session)

        # Get opponent
        opponent = await session.get(Club, opponent_id)
        if not opponent:
            return self._get_default_tactical_plan()

        opponent_strength = opponent.reputation or 5000

        # Adjust style based on match importance
        if match_importance == "title_race":
            style_intensity = "high"
            mentality = "attacking"
        elif match_importance == "relegation_battle":
            style_intensity = "high"
            mentality = "attacking"
        elif match_importance == "easy_match":
            style_intensity = "low"
            mentality = "defensive"
        else:
            style_intensity = "medium"
            mentality = "balanced"

        # Select formation based on available players
        formation = self._select_formation_based_on_squad(
            available_players, context
        )

        return TacticalPlan(
            formation=formation,
            style=context.preferred_style,
            mentality=mentality,
            pressing_intensity=style_intensity,
            focus_area="central",
            risk_level="controlled",
            unavailable_players=available_players,
            tactical_changes=[],
        )

    def _select_formation_based_on_squad(
        self,
        available_players: List[int],
        context: ClubContext,
    ) -> str:
        """Select best formation based on available players."""
        # Count players by position
        position_groups = {
            "GK": [],
            "CB": [], "LB": [], "RB": [], "LWB": [], "RWB": [],
            "CDM": [], "CM": [], "LM": [], "RM": [],
            "CAM": [], "LW": [], "RW": [], "ST": [], "CF": []
        }

        # Get player evaluations (would need to be passed in or fetched)
        # For now, check balance
        gk_count = 0
        cb_count = 0
        etc...

        # Simple formation selection based on available count
        if gk_count >= 1 and cb_count >= 4:
            return "4-3-3"
        elif gk_count >= 1 and cb_count >= 3 and len(available_players) >= 8:
            return "4-2-3-1"
        elif len(available_players) >= 11:
            return "4-4-2"
        else:
            return "4-4-2"

        return "4-3-3"  # Default

    async def make_transfer_decision(
        self,
        transfer_type: TransferDecision,
        context: Dict,
        session: AsyncSession,
    ) -> ManagerDecision:
        """Make a transfer-related decision."""
        # This would integrate with the enhanced transfer engine
        # For now, create a decision structure

        if transfer_type == TransferDecision.IDENTIFY_TARGET:
            decision = ManagerDecision(
                timestamp=date.today(),
                decision_type="transfer",
                category="transfer",
                reasoning="Identifying transfer targets based on squad needs and budget",
                details={"action": "Analyze squad weaknesses and identify 3-5 potential targets"},
                confidence=70,
                status="pending",
            )

        elif transfer_type == TransferDecision.MAKE_OFFER:
            decision = ManagerDecision(
                timestamp=date.today(),
                decision_type="transfer",
                category="transfer",
                reasoning="Will make an offer for the identified target",
                details={"action": "Submit offer to selling club"},
                confidence=65,
                status="pending",
            )

        return decision

    async def generate_transfer_strategy(
        self,
        session: AsyncSession,
    ) -> TransferStrategy:
        """Generate transfer strategy for the window."""
        context = await self.get_club_context(session)

        # Allocate budget based on priorities
        total_budget = context.transfer_budget

        # Base allocation
        strategy = TransferStrategy(
            budget_allocation={
                "GK": int(total_budget * 0.05),
                "CB": int(total_budget * 0.25),
                "LB": int(total_budget * 0.10),
                "RB": int(total_budget * 0.10),
                "CDM": int(total_budget * 0.15),
                "CM": int(total_budget * 0.15),
                "CAM": int(total_budget * 0.10),
                "LM": int(total_budget * 0.08),
                "RM": int(total_budget * 0.08),
                "ST": int(total_budget * 0.12),
                "CF": int(total_budget * 0.12),
            },
        )

        # Priority positions based on squad weaknesses
        strategy.priority_positions = ["ST", "CM", "CB"]

        # Age preferences
        if context.season_objective in ["youth_focus", "develop"]:
            strategy.min_age = 18
            strategy.max_age = 23
        elif context.season_objective in ["win_title"]:
            strategy.min_age = 23
            strategy.max_age = 30
        else:
            strategy.min_age = 20
            strategy.max_age = 28

        # Calculate max single fee
        strategy.max_single_fee = int(total_budget * 0.4)

        return strategy

    async def handle_transfer_offer(
        self,
        offer_id: int,
        action: str,  # "accept", "reject", "counter"
        session: AsyncSession,
    ) -> ManagerDecision:
        """Handle a transfer offer from another club."""
        # Get transfer details
        # This would load the transfer and evaluate

        decision = ManagerDecision(
            timestamp=date.today(),
            decision_type="transfer",
            category="transfer",
            reasoning=f"Decision: {action} for transfer offer {offer_id}",
            details={"offer_id": offer_id, "action": action},
            confidence=80,
            status="pending",
        )

        return decision

    async def process_transfer_window(
        self,
        season_year: int,
        session: AsyncSession,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """Process the entire transfer window."""
        # Generate strategy
        strategy = await self.generate_transfer_strategy(session)

        # Identify targets
        await self.identify_transfer_targets(session)

        # Make offers
        # Monitor negotiations
        # Complete transfers

    async def identify_transfer_targets(
        self,
        session: AsyncSession,
    ) -> None:
        """Identify transfer targets based on squad analysis."""
        context = await self.get_club_context(session)

        # Get players
        result = await session.execute(
            select(Player).where(Player.club_id == self.club_id)
        )
        players = list(result.scalars().all())

        # Identify potential targets based on:
        # 1. Position needs
        # 2. Age profile
        # 3. Performance
        # 4. Contract situation

        targets = []
        for player in players:
            # Check if suitable target
            if self._is_good_transfer_target(player, context):
                targets.append(player)

        # Store evaluations
        await self.evaluate_players(session)

        # Prioritize targets
        targets.sort(
            key=lambda p: (p.potential_ability or 50, -p.age or 25),
            reverse=True
        )

        self.transfer_strategy.early_window_targets = len(targets)

    def _is_good_transfer_target(
        self,
        player: Player,
        context: ClubContext,
    ) -> bool:
        """Check if player is a good transfer target."""
        # Age filter
        if player.age < 18 or player.age > 32:
            return False

        # Ability filter
        if (player.current_ability or 50) < 60:
            return False

        # Squad role
        # Would check from evaluations

        return True

    async def make_tactical_decision(
        self,
        situation: str,  # "trailing", "leading", "tied", "dominating", "struggling"
        session: AsyncSession,
    ) -> ManagerDecision:
        """Make a tactical in-game decision."""
        context = await self.get_club_context(session)

        if situation == "dominating":
            reasoning = "Keep pressing high, maintain momentum"
            decision_type = "tactical"
            details={"action": "maintain_aggressive_style", "intensity": "high"}

        elif situation == "trailing":
            reasoning = "Push for equalizer, commit more players forward"
            decision_type = "tactical"
            details={"action": "become_more_attacking", "push_fullbacks_forward"}

        elif situation == "struggling":
            reasoning = "Defend deep, try to counter"
            decision_type = "tactical"
            details={"action": "switch_to_defensive", "park_the_bus"}

        else:
            reasoning = "Continue balanced approach"
            decision_type = "tactical"
            details={"action": "maintain_balance", "make_substitutions_at_70th_minute"}

        return ManagerDecision(
            timestamp=date.today(),
            decision_type=decision_type,
            category="tactical",
            reasoning=reasoning,
            details=details,
            confidence=75,
            status="approved",
        )

    def get_decision_history(self, limit: int = 20) -> List[ManagerDecision]:
        """Get recent decisions made by the AI manager."""
        return self.decisions[-limit:]

    async def get_season_performance_summary(self, session: AsyncSession) -> Dict:
        """Get performance summary for the season."""
        # Get match results
        context = await self.get_club_context(session)

        summary = {
            "club_id": self.club_id,
            "matches_played": self.matches_managed,
            "points": context.league_points,
            "position": context.league_position,
            "form": context.form,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "win_rate": f"{self.wins / self.matches_managed * 100:.1f}%",
        }

        return summary

    def get_personal_note(self, player_id: int, note_type: str) -> str:
        """Generate personal note for a player."""
        notes = {
            "encouragement": [
                "Continue working hard in training",
                "The manager believes in your potential",
                "Keep improving your fitness",
            ],
            "tactical": [
                "Focus on positioning during matches",
                "Study opponent's weaknesses",
                "Follow the tactical plan",
            ],
            "disciplinary": [
                "Maintain discipline in training",
                "Stay professional on and off the pitch",
                "Respect the staff and teammates",
            ],
            "development": [
                "We want to help you reach your potential",
                "Work on your weaknesses",
                "Additional training on specific skills",
            ],
        }

        if note_type in notes:
            return notes[note_type][0] if notes[note_type] else ""
        return ""

    async def get_pre_match_team_talk(self, opponent: str, session: AsyncSession) -> str:
        """Generate pre-match team talk content."""
        context = await self.get_club_context(session)

        # Would analyze opponent
        talk_points = [
            f"Respect {opponent}'s squad quality",
            f"They've been {context.form}",
            "We need to be focused and disciplined",
        ]

        return f"""Lads, today we face a strong opponent in {opponent}.

{chr(10).join(talk_points)}

Good luck and let's make the fans proud!"""