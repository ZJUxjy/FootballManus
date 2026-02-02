"""AI Manager system for opponent clubs.

AI-controlled clubs can:
- Make transfer decisions
- Adjust tactics
- Manage squad rotation
- Handle contract negotiations
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from fm_manager.core.models import Club, Player, Position
from fm_manager.engine.transfer_engine import TransferEngine, TransferOffer, ContractOffer
from fm_manager.engine.finance_engine import FinanceEngine, ClubFinances

if TYPE_CHECKING:
    from fm_manager.engine.llm_client import LLMClient


class AIPersonality(Enum):
    """AI manager personality types affecting decision making."""
    AGGRESSIVE = "aggressive"      # Risk-taking, attacks, high pressing
    BALANCED = "balanced"          # Standard approach
    DEFENSIVE = "defensive"        # Conservative, counter-attacking
    TIKI_TAKA = "tiki_taka"        # Possession-based
    LONG_BALL = "long_ball"        # Direct play
    YOUTH_FOCUS = "youth_focus"    # Prioritizes young players
    MONEYBALL = "moneyball"        # Data-driven, value-focused
    SUPERSTAR = "superstar"        # Wants star players
    LLM_POWERED = "llm_powered"    # Uses LLM for complex decisions


class AIStyle(Enum):
    """Playing style preferences."""
    POSSESSION = "possession"      # Keep the ball
    COUNTER = "counter"            # Hit on the break
    HIGH_PRESS = "high_press"      # Press high up the pitch
    LOW_BLOCK = "low_block"        # Defend deep
    BALANCED = "balanced"          # Flexible approach


@dataclass
class AISquadAssessment:
    """AI's assessment of its squad."""
    club_id: int
    
    # Strength by position
    goalkeeper_strength: int = 50
    defense_strength: int = 50
    midfield_strength: int = 50
    attack_strength: int = 50
    
    # Depth
    squad_depth: int = 50  # 0-100
    
    # Age profile
    average_age: float = 25.0
    
    # Weaknesses
    needs: list[Position] = field(default_factory=list)
    
    # Key players
    star_players: list[int] = field(default_factory=list)  # Player IDs
    deadwood: list[int] = field(default_factory=list)  # Players to sell
    
    def to_dict(self) -> dict:
        return {
            "goalkeeper": self.goalkeeper_strength,
            "defense": self.defense_strength,
            "midfield": self.midfield_strength,
            "attack": self.attack_strength,
            "needs": [p.value for p in self.needs],
            "squad_depth": self.squad_depth,
        }


@dataclass
class AITransferStrategy:
    """AI's transfer strategy."""
    priority_positions: list[Position] = field(default_factory=list)
    max_budget: int = 0
    max_wage: int = 0
    age_preference: tuple[int, int] = (23, 28)  # min, max
    min_potential: int = 70
    sell_threshold: int = 80  # Willing to sell if offer > value * threshold
    
    # Strategy flags
    buy_loan_only: bool = False
    focus_free_agents: bool = False
    sell_deadwood_first: bool = True


@dataclass
class AITacticalSetup:
    """AI's tactical preferences."""
    formation: str = "4-3-3"
    style: AIStyle = AIStyle.BALANCED
    mentality: str = "balanced"  # attacking, balanced, defensive
    
    # In-match adjustments
    leads_by_one: str = "cautious"  # How to play when leading
    trails_by_one: str = "attacking"  # How to play when trailing
    
    # Player instructions
    key_player_role: str = "playmaker"
    target_man: int | None = None  # Player ID


@dataclass
class AIMatchDecision:
    """AI's match-time decision."""
    minute: int
    decision_type: str  # substitution, tactic_change, instruction
    
    # For substitutions
    player_out: int | None = None
    player_in: int | None = None
    reason: str = ""
    
    # For tactic changes
    new_mentality: str | None = None
    new_style: AIStyle | None = None


class LLMManagerDecisionMaker:
    """LLM-powered decision maker for AI managers.
    
    This class uses LLM to make complex managerial decisions.
    """
    
    def __init__(self, llm_client: "LLMClient"):
        self.llm = llm_client
    
    def decide_transfer_offer(
        self,
        player: Player,
        offer: TransferOffer,
        club: Club,
        squad_assessment: AISquadAssessment,
    ) -> dict:
        """Use LLM to decide on a transfer offer."""
        if not self.llm:
            return {"decision": "counter", "reasoning": "LLM not available"}
        
        prompt = f"""You are the manager of {club.name}. A transfer offer has come in for one of your players.

Player: {player.full_name}
Position: {player.position.value if player.position else 'Unknown'}
Age: {player.age or 25}
Current Ability: {player.current_ability or 50}/100
Contract: {getattr(player, 'contract_until', None) or 'Unknown'}

Offer: €{offer.fee:,} from {offer.from_club_id}

Squad Context:
- Star players: {len(squad_assessment.star_players)}
- Needs: {[p.value for p in squad_assessment.needs]}
- Is this player a star? {player.id in squad_assessment.star_players if player.id else False}

Should you:
1. ACCEPT the offer
2. REJECT the offer  
3. COUNTER with higher fee

Respond in JSON format:
{{
    "decision": "accept|reject|counter",
    "counter_fee": <amount if countering>,
    "reasoning": "<brief explanation>"
}}"""
        
        try:
            response = self.llm.generate(prompt, max_tokens=300, temperature=0.3)
            result = json.loads(response.content)
            return result
        except Exception:
            # Fallback to rule-based
            return {"decision": "counter", "reasoning": "Using fallback strategy"}
    
    def decide_tactics(
        self,
        opponent: Club,
        key_players_available: list[Player],
        recent_form: str,
    ) -> dict:
        """Use LLM to decide match tactics."""
        if not self.llm:
            return {"formation": "4-3-3", "style": "balanced", "reasoning": "Default"}
        
        players_str = "\n".join([
            f"- {p.full_name} ({p.position.value if p.position else 'Unknown'}, CA{p.current_ability or 50})"
            for p in key_players_available[:5]
        ])
        
        prompt = f"""You are preparing tactics for the next match.

Opponent: {opponent.name} (Reputation: {opponent.reputation or 5000})
Your recent form: {recent_form}

Key available players:
{players_str}

Decide your tactical approach:
- Formation (e.g., 4-3-3, 4-4-2, 3-5-2)
- Style (possession, counter-attack, high-press, balanced)
- Mentality (attacking, balanced, defensive)

Respond in JSON:
{{
    "formation": "<formation>",
    "style": "<style>",
    "mentality": "<mentality>",
    "reasoning": "<brief explanation>"
}}"""
        
        try:
            response = self.llm.generate(prompt, max_tokens=250, temperature=0.4)
            result = json.loads(response.content)
            return result
        except Exception:
            return {"formation": "4-3-3", "style": "balanced", "mentality": "balanced", "reasoning": "Default fallback"}
    
    def decide_substitution(
        self,
        minute: int,
        score_for: int,
        score_against: int,
        tired_players: list[Player],
        available_subs: list[Player],
        recent_decisions: list[str],
    ) -> dict:
        """Use LLM to decide on a substitution."""
        if not self.llm or minute < 60:
            return {"make_change": False}
        
        tired_str = "\n".join([f"- {p.full_name} ({p.position.value if p.position else 'Unknown'})" for p in tired_players[:3]])
        subs_str = "\n".join([f"- {p.full_name} ({p.position.value if p.position else 'Unknown'}, CA{p.current_ability or 50})" for p in available_subs[:3]])
        
        prompt = f"""Match situation:
- Minute: {minute}'
- Score: {score_for}-{score_against}
- Recent decisions: {recent_decisions[-3:] if recent_decisions else 'None'}

Tired players on pitch:
{tired_str}

Available substitutes:
{subs_str}

Should you make a substitution? If yes, who should come off and who should come on?

Respond in JSON:
{{
    "make_change": true|false,
    "player_out": "<name or null>",
    "player_in": "<name or null>",
    "reasoning": "<explanation>"
}}"""
        
        try:
            response = self.llm.generate(prompt, max_tokens=200, temperature=0.3)
            result = json.loads(response.content)
            return result
        except Exception:
            return {"make_change": False}
    
    def generate_post_match_comments(
        self,
        won: bool,
        drawn: bool,
        goals_for: int,
        goals_against: int,
        opponent: Club,
        key_moments: list[str],
    ) -> str:
        """Generate post-match comments using LLM."""
        if not self.llm:
            if won:
                return "Pleased with the result. The lads worked hard today."
            elif drawn:
                return "A point is a point. We could have done better."
            else:
                return "Disappointed with the result. We need to improve."
        
        result_str = "Win" if won else ("Draw" if drawn else "Loss")
        moments_str = "\n".join([f"- {m}" for m in key_moments[:3]])
        
        prompt = f"""Generate post-match comments as a football manager.

Result: {result_str} ({goals_for}-{goals_against} vs {opponent.name})
Key moments:
{moments_str}

Write 2-3 sentences in the style of a manager speaking to the media."""
        
        try:
            response = self.llm.generate(prompt, max_tokens=150, temperature=0.7)
            return response.content.strip()
        except Exception:
            return "Good performance from the lads today."


class AIManager:
    """AI manager controlling a club."""
    
    def __init__(
        self,
        club: Club,
        personality: AIPersonality = AIPersonality.BALANCED,
        llm_client: "LLMClient" | None = None,
    ):
        self.club = club
        self.personality = personality
        self.llm = llm_client
        
        # Initialize LLM decision maker if LLM available and personality is LLM-powered
        self.llm_decision_maker: LLMManagerDecisionMaker | None = None
        if llm_client and personality == AIPersonality.LLM_POWERED:
            self.llm_decision_maker = LLMManagerDecisionMaker(llm_client)
        
        # AI state - initialize tactics first (needed by _init_personality)
        self.squad_assessment: AISquadAssessment | None = None
        self.transfer_strategy: AITransferStrategy | None = None
        self.tactics: AITacticalSetup = AITacticalSetup()
        
        # Initialize based on personality (after tactics is set)
        self._init_personality()
        
        # Transfer tracking
        self.transfer_targets: list[Player] = []
        self.players_listed: list[int] = []  # Player IDs for sale
        
        # Season tracking
        self.matches_played = 0
        self.matches_won = 0
        self.matches_drawn = 0
        self.matches_lost = 0
        self.recent_decisions: list[str] = []
    
    def _init_personality(self) -> None:
        """Initialize traits based on personality."""
        personality_traits = {
            AIPersonality.AGGRESSIVE: {
                "style": AIStyle.HIGH_PRESS,
                "mentality": "attacking",
                "risk_tolerance": 0.8,
                "youth_preference": 0.3,
            },
            AIPersonality.DEFENSIVE: {
                "style": AIStyle.LOW_BLOCK,
                "mentality": "defensive",
                "risk_tolerance": 0.2,
                "youth_preference": 0.4,
            },
            AIPersonality.TIKI_TAKA: {
                "style": AIStyle.POSSESSION,
                "mentality": "balanced",
                "risk_tolerance": 0.5,
                "youth_preference": 0.6,
            },
            AIPersonality.LONG_BALL: {
                "style": AIStyle.COUNTER,
                "mentality": "attacking",
                "risk_tolerance": 0.6,
                "youth_preference": 0.3,
            },
            AIPersonality.YOUTH_FOCUS: {
                "style": AIStyle.BALANCED,
                "mentality": "balanced",
                "risk_tolerance": 0.5,
                "youth_preference": 0.9,
            },
            AIPersonality.MONEYBALL: {
                "style": AIStyle.BALANCED,
                "mentality": "balanced",
                "risk_tolerance": 0.4,
                "youth_preference": 0.7,
            },
            AIPersonality.SUPERSTAR: {
                "style": AIStyle.POSSESSION,
                "mentality": "attacking",
                "risk_tolerance": 0.6,
                "youth_preference": 0.2,
            },
            AIPersonality.BALANCED: {
                "style": AIStyle.BALANCED,
                "mentality": "balanced",
                "risk_tolerance": 0.5,
                "youth_preference": 0.5,
            },
            AIPersonality.LLM_POWERED: {
                "style": AIStyle.BALANCED,
                "mentality": "balanced",
                "risk_tolerance": 0.5,
                "youth_preference": 0.5,
            },
        }
        
        traits = personality_traits.get(self.personality, personality_traits[AIPersonality.BALANCED])
        self.risk_tolerance = traits["risk_tolerance"]
        self.youth_preference = traits["youth_preference"]
        self.tactics.style = traits["style"]
        self.tactics.mentality = traits["mentality"]
    
    def assess_squad(self, players: list[Player]) -> AISquadAssessment:
        """Assess current squad strength and needs."""
        assessment = AISquadAssessment(club_id=self.club.id or 0)
        
        # Calculate strength by position
        position_players: dict[Position, list[Player]] = {}
        for player in players:
            pos = player.position
            if pos not in position_players:
                position_players[pos] = []
            position_players[pos].append(player)
        
        # Average ability by position group
        gk_players = position_players.get(Position.GK, [])
        def_players = [p for p in players if p.position in {
            Position.CB, Position.LB, Position.RB, Position.LWB, Position.RWB
        }]
        mid_players = [p for p in players if p.position in {
            Position.CDM, Position.CM, Position.CAM, Position.LM, Position.RM
        }]
        att_players = [p for p in players if p.position in {
            Position.LW, Position.RW, Position.ST, Position.CF
        }]
        
        assessment.goalkeeper_strength = self._avg_ability(gk_players)
        assessment.defense_strength = self._avg_ability(def_players)
        assessment.midfield_strength = self._avg_ability(mid_players)
        assessment.attack_strength = self._avg_ability(att_players)
        
        # Calculate squad depth
        assessment.squad_depth = min(100, len(players) * 3)
        
        # Calculate average age
        if players:
            assessment.average_age = sum(p.age or 25 for p in players) / len(players)
        
        # Identify needs (weakest positions)
        strengths = {
            Position.GK: assessment.goalkeeper_strength,
            "DEF": assessment.defense_strength,
            "MID": assessment.midfield_strength,
            "ATT": assessment.attack_strength,
        }
        
        needs = []
        if assessment.goalkeeper_strength < 60:
            needs.append(Position.GK)
        if assessment.defense_strength < assessment.midfield_strength - 10:
            needs.extend([Position.CB, Position.LB])
        if assessment.midfield_strength < 60:
            needs.extend([Position.CM, Position.CDM])
        if assessment.attack_strength < 60:
            needs.extend([Position.ST, Position.LW])
        
        assessment.needs = needs[:3]  # Top 3 priorities
        
        # Identify star players and deadwood
        for player in players:
            ca = player.current_ability or 50
            age = player.age or 25
            
            if ca >= 75:
                assessment.star_players.append(player.id or 0)
            elif ca < 50 and age > 28:
                assessment.deadwood.append(player.id or 0)
        
        self.squad_assessment = assessment
        return assessment
    
    def _avg_ability(self, players: list[Player]) -> int:
        """Calculate average current ability."""
        if not players:
            return 50
        return int(sum(p.current_ability or 50 for p in players) / len(players))
    
    def create_transfer_strategy(
        self,
        finances: ClubFinances,
        current_squad: list[Player],
    ) -> AITransferStrategy:
        """Create transfer strategy based on squad needs and finances."""
        strategy = AITransferStrategy()
        
        # Use squad assessment
        if not self.squad_assessment:
            self.assess_squad(current_squad)
        
        assessment = self.squad_assessment
        assert assessment is not None
        
        # Set priorities based on needs
        strategy.priority_positions = assessment.needs[:2]
        
        # Set budget
        strategy.max_budget = finances.transfer_budget
        strategy.max_wage = finances.wage_budget * 0.8  # 80% of wage budget
        
        # Age preference based on personality
        if self.personality == AIPersonality.YOUTH_FOCUS:
            strategy.age_preference = (16, 22)
            strategy.min_potential = 75
        elif self.personality == AIPersonality.SUPERSTAR:
            strategy.age_preference = (25, 30)
            strategy.min_potential = 50
        else:
            strategy.age_preference = (22, 28)
            strategy.min_potential = 65
        
        # Sell threshold based on club needs
        if assessment.squad_depth > 80:
            strategy.sell_threshold = 70  # More willing to sell
        else:
            strategy.sell_threshold = 90  # Hold onto players
        
        # Special strategies
        if finances.balance < 0:
            strategy.buy_loan_only = True
            strategy.sell_deadwood_first = True
        
        if self.personality == AIPersonality.MONEYBALL:
            strategy.focus_free_agents = True
            strategy.sell_threshold = 85
        
        self.transfer_strategy = strategy
        return strategy
    
    def decide_on_transfer_offer(
        self,
        offer: TransferOffer,
        player: Player,
        transfer_engine: TransferEngine,
    ) -> dict:
        """Decide whether to accept a transfer offer."""
        # Use LLM if available and personality is LLM-powered
        if self.llm_decision_maker and self.squad_assessment:
            return self.llm_decision_maker.decide_transfer_offer(
                player, offer, self.club, self.squad_assessment
            )
        
        # Otherwise use rule-based
        evaluation = transfer_engine.evaluate_transfer_offer(
            offer, player, self.club, None  # type: ignore
        )
        
        # AI personality adjustments
        decision = evaluation["decision"]
        score = evaluation["score"]
        
        # Star player reluctance
        if player.id in (self.squad_assessment.star_players if self.squad_assessment else []):
            score -= 20  # Harder to sell stars
        
        # Youth focus preference
        if self.personality == AIPersonality.YOUTH_FOCUS and (player.age or 25) < 21:
            score -= 15  # Reluctant to sell youth
        
        # Moneyball approach
        if self.personality == AIPersonality.MONEYBALL:
            if score >= 80:  # Will sell for good profit
                decision = "accept"
        
        # Superstar wants to keep stars
        if self.personality == AIPersonality.SUPERSTAR:
            if (player.current_ability or 50) > 75:
                score -= 25
                if score < 75:
                    decision = "reject"
        
        return {
            "decision": decision,
            "score": max(0, min(100, score)),
            "reasoning": self._generate_decision_reasoning(player, decision),
        }
    
    def _generate_decision_reasoning(self, player: Player, decision: str) -> str:
        """Generate reasoning for transfer decision."""
        reasons = {
            "accept": [
                f"The offer for {player.full_name} represents good value.",
                f"Time to cash in on {player.full_name}.",
                f"The fee allows us to reinvest in the squad.",
            ],
            "reject": [
                f"{player.full_name} is too important to sell.",
                f"We need {player.full_name} for our ambitions.",
                f"The offer doesn't meet our valuation.",
            ],
            "counter": [
                f"We're open to selling {player.full_name} for the right price.",
                f"Interesting offer, but we need more for {player.full_name}.",
            ],
        }
        
        return random.choice(reasons.get(decision, ["Under consideration."]))
    
    def identify_transfer_targets(
        self,
        available_players: list[Player],
        transfer_engine: TransferEngine,
    ) -> list[Player]:
        """Identify potential transfer targets."""
        if not self.transfer_strategy:
            return []
        
        strategy = self.transfer_strategy
        targets = []
        
        for player in available_players:
            # Check position need
            if player.position not in strategy.priority_positions:
                continue
            
            # Check age
            age = player.age or 25
            if not (strategy.age_preference[0] <= age <= strategy.age_preference[1]):
                continue
            
            # Check potential
            if (player.potential_ability or 50) < strategy.min_potential:
                continue
            
            # Check affordability
            value = transfer_engine.valuation_calculator.calculate_value(player)
            if value > strategy.max_budget:
                continue
            
            # Check wages
            if player.salary and player.salary > strategy.max_wage:
                continue
            
            targets.append(player)
        
        # Sort by value (best first)
        targets.sort(
            key=lambda p: (p.current_ability or 50) + (p.potential_ability or 50) / 2,
            reverse=True
        )
        
        self.transfer_targets = targets[:10]  # Keep top 10
        return self.transfer_targets
    
    def prepare_match_tactics(
        self,
        opponent: Club,
        key_players: list[Player],
    ) -> dict:
        """Prepare tactics for upcoming match."""
        # Use LLM if available and personality is LLM-powered
        if self.llm_decision_maker:
            return self.llm_decision_maker.decide_tactics(
                opponent, key_players, self.get_form()
            )
        
        # Otherwise use personality-based
        return {
            "formation": self.tactics.formation,
            "style": self.tactics.style.value,
            "mentality": self.tactics.mentality,
            "reasoning": f"Standard {self.personality.value} approach",
        }
    
    def make_transfer_offer(
        self,
        target: Player,
        target_club: Club,
        transfer_engine: TransferEngine,
    ) -> TransferOffer | None:
        """Make a transfer offer for a target player."""
        # Calculate offer amount
        value = transfer_engine.valuation_calculator.calculate_value(target)
        
        # AI personality affects offer
        if self.personality == AIPersonality.MONEYBALL:
            offer_amount = int(value * 0.85)  # Try to get bargain
        elif self.personality == AIPersonality.SUPERSTAR:
            offer_amount = int(value * 1.2)  # Overpay for stars
        else:
            offer_amount = int(value * 0.95)  # Slightly under value
        
        # Check budget
        if not self.transfer_strategy:
            return None
        
        if offer_amount > self.transfer_strategy.max_budget:
            offer_amount = int(self.transfer_strategy.max_budget * 0.9)
        
        return transfer_engine.create_transfer_offer(
            player=target,
            from_club=self.club,
            to_club=target_club,
            fee=offer_amount,
        )
    
    def make_match_decision(
        self,
        minute: int,
        score_for: int,
        score_against: int,
        available_subs: list[Player],
        tired_players: list[Player],
    ) -> AIMatchDecision | None:
        """Make an in-match decision."""
        # Use LLM for complex decisions if available and personality is LLM-powered
        if self.llm_decision_maker and minute >= 60:
            llm_decision = self.llm_decision_maker.decide_substitution(
                minute, score_for, score_against, tired_players, available_subs, self.recent_decisions
            )
            
            if llm_decision.get("make_change") and llm_decision.get("player_out") and llm_decision.get("player_in"):
                # Find player IDs from names
                player_out_name = llm_decision["player_out"]
                player_in_name = llm_decision["player_in"]
                
                player_out = next((p for p in tired_players if p.full_name == player_out_name), None)
                player_in = next((p for p in available_subs if p.full_name == player_in_name), None)
                
                if player_out and player_in:
                    decision = AIMatchDecision(
                        minute=minute,
                        decision_type="substitution",
                        player_out=player_out.id,
                        player_in=player_in.id,
                        reason=llm_decision.get("reasoning", "LLM recommended"),
                    )
                    self.recent_decisions.append(f"Sub {minute}': {player_out_name} -> {player_in_name}")
                    return decision
        
        # Fall back to rule-based
        score_diff = score_for - score_against
        
        # Decision logic based on score and time
        if minute < 60:
            # Early game - rarely make changes
            if tired_players and random.random() < 0.1:
                return self._make_substitution(minute, tired_players[0], available_subs)
            return None
        
        elif minute < 75:
            # Mid-late game
            if score_diff < 0 and self.tactics.mentality != "attacking":
                # Losing - push for equalizer
                return AIMatchDecision(
                    minute=minute,
                    decision_type="tactic_change",
                    new_mentality="attacking",
                    reason="Chasing the game",
                )
            
            if tired_players and random.random() < 0.3:
                return self._make_substitution(minute, tired_players[0], available_subs)
        
        else:
            # Late game
            if score_diff > 0 and self.tactics.mentality != "defensive":
                # Winning - protect lead
                return AIMatchDecision(
                    minute=minute,
                    decision_type="tactic_change",
                    new_mentality="defensive",
                    reason="Protecting the lead",
                )
            
            if score_diff < 0:
                # Desperate - all out attack
                if tired_players:
                    return self._make_substitution(minute, tired_players[0], available_subs, attack=True)
        
        return None
    
    def _make_substitution(
        self,
        minute: int,
        player_out: Player,
        available_subs: list[Player],
        attack: bool = False,
    ) -> AIMatchDecision | None:
        """Decide on a substitution."""
        if not available_subs:
            return None
        
        # Choose replacement based on need
        if attack:
            # Prefer attackers
            subs = [p for p in available_subs if p.position in {
                Position.ST, Position.CF, Position.LW, Position.RW
            }]
        else:
            subs = available_subs
        
        if not subs:
            subs = available_subs
        
        # Pick best available
        subs.sort(key=lambda p: p.current_ability or 50, reverse=True)
        player_in = subs[0]
        
        decision = AIMatchDecision(
            minute=minute,
            decision_type="substitution",
            player_out=player_out.id,
            player_in=player_in.id,
            reason="Fresh legs needed" if not attack else "Chasing the game",
        )
        self.recent_decisions.append(f"Sub {minute}': {player_out.full_name} -> {player_in.full_name}")
        return decision
    
    def generate_post_match_comments(
        self,
        won: bool,
        drawn: bool,
        goals_for: int,
        goals_against: int,
        opponent: Club,
        key_moments: list[str],
    ) -> str:
        """Generate post-match comments."""
        if self.llm_decision_maker:
            return self.llm_decision_maker.generate_post_match_comments(
                won, drawn, goals_for, goals_against, opponent, key_moments
            )
        
        # Default comments
        if won:
            return f"Pleased with the result against {opponent.name}. The lads worked hard today."
        elif drawn:
            return f"A point against {opponent.name} is acceptable. We could have done better."
        else:
            return f"Disappointed to lose to {opponent.name}. We need to improve."
    
    def update_after_match(self, won: bool, drawn: bool, goals_for: int, goals_against: int) -> None:
        """Update AI state after a match."""
        self.matches_played += 1
        
        if won:
            self.matches_won += 1
        elif drawn:
            self.matches_drawn += 1
        else:
            self.matches_lost += 1
        
        # Clear recent decisions
        self.recent_decisions = []
    
    def get_form(self) -> str:
        """Get current form description."""
        if self.matches_played < 3:
            return "Unknown"
        
        recent_win_rate = self.matches_won / self.matches_played
        
        if recent_win_rate >= 0.7:
            return "Excellent"
        elif recent_win_rate >= 0.5:
            return "Good"
        elif recent_win_rate >= 0.3:
            return "Average"
        else:
            return "Poor"
    
    def should_sell_player(self, player: Player, offer_amount: int) -> bool:
        """Determine if player should be sold."""
        if not self.transfer_strategy:
            return False
        
        from fm_manager.engine.transfer_engine import TransferValuationCalculator
        calculator = TransferValuationCalculator()
        value = calculator.calculate_value(player)
        
        # Check threshold
        threshold_multiplier = self.transfer_strategy.sell_threshold / 100
        
        # Personality adjustments
        if self.personality == AIPersonality.MONEYBALL:
            threshold_multiplier = 0.85  # Sell for profit
        elif self.personality == AIPersonality.SUPERSTAR and (player.current_ability or 50) > 75:
            threshold_multiplier = 1.5  # Hard to sell stars
        
        return offer_amount >= value * threshold_multiplier


class AIManagerController:
    """Controller managing all AI managers in the game."""
    
    def __init__(self, llm_client: "LLMClient" | None = None):
        self.managers: dict[int, AIManager] = {}  # club_id -> AIManager
        self.transfer_engine = TransferEngine()
        self.finance_engine = FinanceEngine()
        self.llm_client = llm_client
    
    def create_manager(
        self,
        club: Club,
        personality: AIPersonality | None = None,
        use_llm: bool = False,
    ) -> AIManager:
        """Create an AI manager for a club."""
        if personality is None:
            # Assign personality based on club reputation
            if club.reputation and club.reputation > 8000:
                personality = random.choice([
                    AIPersonality.SUPERSTAR,
                    AIPersonality.TIKI_TAKA,
                    AIPersonality.AGGRESSIVE,
                ])
            elif club.reputation and club.reputation < 4000:
                personality = random.choice([
                    AIPersonality.LONG_BALL,
                    AIPersonality.DEFENSIVE,
                    AIPersonality.YOUTH_FOCUS,
                ])
            else:
                personality = random.choice(list(AIPersonality))
        
        # Use LLM if requested and available
        llm = self.llm_client if use_llm or personality == AIPersonality.LLM_POWERED else None
        
        manager = AIManager(club, personality, llm)
        self.managers[club.id or 0] = manager
        return manager
    
    def process_transfer_window(
        self,
        clubs: list[Club],
        players: list[Player],
        current_date: date,
    ) -> list[dict]:
        """Process AI transfer activity during a window."""
        if not self.transfer_engine.window_manager.is_window_open(current_date):
            return []
        
        transfers = []
        
        for club in clubs:
            if club.id not in self.managers:
                continue
            
            manager = self.managers[club.id]
            
            # Assess squad
            club_players = [p for p in players if p.club_id == club.id]
            
            # Create finances
            finances = ClubFinances(
                club_id=club.id or 0,
                balance=club.balance,
                wage_budget=3_000_000,
                transfer_budget=50_000_000,
            )
            
            # Create strategy
            strategy = manager.create_transfer_strategy(finances, club_players)
            
            # Identify targets from other clubs
            other_players = [p for p in players if p.club_id != club.id and p.club_id]
            targets = manager.identify_transfer_targets(other_players, self.transfer_engine)
            
            # Make offers
            for target in targets[:3]:  # Try for top 3
                target_club_id = target.club_id
                if not target_club_id:
                    continue
                
                target_club = next((c for c in clubs if c.id == target_club_id), None)
                if not target_club:
                    continue
                
                offer = manager.make_transfer_offer(target, target_club, self.transfer_engine)
                
                if offer:
                    transfers.append({
                        "from_club": club.name,
                        "to_club": target_club.name,
                        "player": target.full_name,
                        "fee": offer.fee,
                        "status": "pending",
                    })
        
        return transfers
    
    def get_manager(self, club_id: int) -> AIManager | None:
        """Get AI manager for a club."""
        return self.managers.get(club_id)
