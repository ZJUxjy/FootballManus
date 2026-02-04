"""Finance engine for FM Manager.

Handles all financial aspects of club management:
- Revenue: matchday, TV rights, commercial, prize money
- Expenses: wages, transfers, facilities, staff
- FFP (Financial Fair Play) compliance
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum, auto
from typing import Callable, Union, List, Tuple

from fm_manager.core.models import Club, League, Match, MatchStatus, Player


class RevenueType(Enum):
    """Types of revenue."""
    MATCHDAY = auto()           # Ticket sales
    TV_RIGHTS = auto()          # Broadcasting
    COMMERCIAL = auto()         # Sponsorships
    PRIZE_MONEY = auto()        # League/cup prizes
    PLAYER_SALES = auto()       # Transfer income
    OTHER = auto()


class ExpenseType(Enum):
    """Types of expenses."""
    WAGES = auto()              # Player salaries
    TRANSFER_FEE = auto()       # Transfer expenditure
    AGENT_FEES = auto()         # Agent commissions
    YOUTH_INVESTMENT = auto()   # Academy costs
    STAFF_WAGES = auto()        # Non-player staff
    FACILITIES = auto()         # Stadium/training ground
    SCOUTING = auto()           # Scouting network
    INTEREST = auto()           # Loan interest
    OTHER = auto()


@dataclass
class FinancialTransaction:
    """A single financial transaction."""
    date: date
    amount: int
    type: Union[RevenueType, ExpenseType]
    description: str
    category: str = ""  # "revenue" or "expense"


@dataclass
class WeeklyFinances:
    """Financial summary for a week."""
    week_start: date
    
    # Revenue
    matchday_revenue: int = 0
    tv_revenue: int = 0
    commercial_revenue: int = 0
    other_revenue: int = 0
    
    # Expenses
    wage_bill: int = 0
    transfer_expenditure: int = 0
    other_expenses: int = 0
    
    @property
    def total_revenue(self) -> int:
        return self.matchday_revenue + self.tv_revenue + self.commercial_revenue + self.other_revenue
    
    @property
    def total_expenses(self) -> int:
        return self.wage_bill + self.transfer_expenditure + self.other_expenses
    
    @property
    def net_result(self) -> int:
        return self.total_revenue - self.total_expenses


@dataclass
class ClubFinances:
    """Complete financial state for a club."""
    club_id: int
    
    # Current balance
    balance: int = 0
    
    # Budgets (weekly)
    wage_budget: int = 0
    transfer_budget: int = 0
    weekly_wage_bill: int = 0
    
    # Revenue settings
    ticket_price: int = 50
    season_ticket_holders: int = 0
    average_attendance: int = 0
    
    # Financial history
    weekly_history: List[WeeklyFinances] = field(default_factory=list)
    transactions: List[FinancialTransaction] = field(default_factory=list)
    
    # FFP tracking
    ffp_three_year_loss: int = 0
    ffp_compliant: bool = True
    
    def add_transaction(self, transaction: FinancialTransaction) -> None:
        """Add a transaction and update balance."""
        self.transactions.append(transaction)
        if transaction.category == "revenue":
            self.balance += transaction.amount
        else:
            self.balance -= transaction.amount
    
    def get_monthly_summary(self, year: int, month: int) -> dict:
        """Get financial summary for a month."""
        month_transactions = [
            t for t in self.transactions
            if t.date.year == year and t.date.month == month
        ]
        
        revenue = sum(t.amount for t in month_transactions if t.category == "revenue")
        expenses = sum(t.amount for t in month_transactions if t.category == "expense")
        
        return {
            "revenue": revenue,
            "expenses": expenses,
            "net": revenue - expenses,
            "transaction_count": len(month_transactions),
        }


class FinanceCalculator:
    """Calculate financial values for clubs."""
    
    # Constants for revenue calculation
    BASE_TICKET_PRICE = 50  # Currency units
    ATTENDANCE_FACTOR = 0.95  # 95% capacity for big games
    TV_REVENUE_PER_MATCH = 2_000_000  # Base TV revenue
    
    # Sponsorship tiers based on reputation
    SPONSORSHIP_TIERS = {
        (0, 2000): 500_000,      # Very low reputation
        (2000, 4000): 2_000_000,  # Low reputation
        (4000, 6000): 5_000_000,  # Medium reputation
        (6000, 8000): 12_000_000, # High reputation
        (8000, 10000): 30_000_000, # Very high reputation
    }
    
    def __init__(self):
        pass
    
    def calculate_matchday_revenue(
        self,
        club: Club,
        attendance_percent: float = 0.85,
        is_derby: bool = False,
        is_title_race: bool = False,
    ) -> int:
        """Calculate matchday revenue from ticket sales.
        
        Args:
            club: The club
            attendance_percent: Stadium fill percentage (0-1)
            is_derby: Whether it's a derby match (higher demand)
            is_title_race: Whether it's a title decider
        
        Returns:
            Revenue in currency units
        """
        base_capacity = club.stadium_capacity or 30000
        
        # Adjust attendance for big games
        if is_derby:
            attendance_percent = min(1.0, attendance_percent * 1.15)
        if is_title_race:
            attendance_percent = min(1.0, attendance_percent * 1.10)
        
        attendance = int(base_capacity * attendance_percent)
        
        # Ticket pricing tiers
        # Premium seats (20% of capacity) at 3x price
        # Standard seats (80% of capacity) at normal price
        premium_seats = int(attendance * 0.2)
        standard_seats = attendance - premium_seats
        
        ticket_price = club.ticket_price or self.BASE_TICKET_PRICE
        premium_price = ticket_price * 3
        
        revenue = (premium_seats * premium_price) + (standard_seats * ticket_price)
        
        return revenue
    
    def calculate_tv_revenue(
        self,
        club: Club,
        league: League,
        league_position: int = 10,
        is_live_match: bool = True,
    ) -> int:
        """Calculate TV broadcasting revenue.
        
        Revenue is distributed based on:
        - League popularity (bigger leagues = more money)
        - Team performance (higher finish = more money)
        - Live broadcast bonus
        """
        # Base amount depends on league tier
        base_revenue = self.TV_REVENUE_PER_MATCH
        
        # League multiplier (top 5 leagues get more)
        if league.country in ["England", "Spain", "Germany", "Italy", "France"]:
            league_multiplier = 3.0
        else:
            league_multiplier = 1.0
        
        # Performance bonus (top teams get more)
        # Linear distribution: position 1 gets 2x, last gets 0.5x
        num_teams = league.teams_count or 20
        position_factor = 2.0 - (1.5 * (league_position - 1) / (num_teams - 1))
        position_factor = max(0.5, min(2.0, position_factor))
        
        # Live match bonus
        live_bonus = 1.5 if is_live_match else 1.0
        
        total_revenue = int(base_revenue * league_multiplier * position_factor * live_bonus)
        
        return total_revenue
    
    def calculate_commercial_revenue(self, club: Club) -> int:
        """Calculate annual commercial revenue (sponsorships, merchandise).
        
        Based on club reputation and fanbase.
        """
        reputation = club.reputation or 1000
        
        # Find sponsorship tier
        annual_sponsorship = 1_000_000  # Default
        for (min_rep, max_rep), amount in self.SPONSORSHIP_TIERS.items():
            if min_rep <= reputation < max_rep:
                annual_sponsorship = amount
                break
        
        if reputation >= 10000:
            annual_sponsorship = 80_000_000  # Elite clubs
        
        # Weekly amount
        weekly_revenue = annual_sponsorship // 52
        
        return weekly_revenue
    
    def calculate_season_prize_money(
        self,
        club: Club,
        league: League,
        final_position: int,
    ) -> int:
        """Calculate end-of-season prize money.
        
        Higher finish = more money.
        """
        # Prize pool based on league
        if league.country == "England":
            total_pool = 2_500_000_000  # Premier League has huge prize pool
        elif league.country in ["Spain", "Germany", "Italy"]:
            total_pool = 1_500_000_000
        else:
            total_pool = 500_000_000
        
        # Distribution: exponential decay based on position
        # Position 1 gets ~20% of pool, position 20 gets ~2%
        num_teams = league.teams_count or 20
        position_weight = (num_teams - final_position + 1) ** 2
        total_weight = sum((num_teams - i + 1) ** 2 for i in range(1, num_teams + 1))
        
        share = position_weight / total_weight
        prize_money = int(total_pool * share)
        
        return prize_money
    
    def calculate_weekly_wage_bill(self, players: List[Player]) -> int:
        """Calculate total weekly wages for a squad."""
        return sum(p.salary for p in players)
    
    def calculate_transfer_budget_recommendation(
        self,
        club: Club,
        current_balance: int,
        projected_revenue: int,
    ) -> int:
        """Recommend a transfer budget based on financial health.
        
        Conservative approach: 
        - 20% of balance + 10% of projected revenue
        - Capped at 50% of balance
        """
        from_balance = int(current_balance * 0.20)
        from_revenue = int(projected_revenue * 0.10)
        
        recommended = from_balance + from_revenue
        maximum = int(current_balance * 0.50)  # Don't spend more than 50% of balance
        
        return min(recommended, maximum)


class FFPCalculator:
    """Financial Fair Play calculator."""
    
    # FFP Rules (simplified)
    MAX_THREE_YEAR_LOSS = 30_000_000  # €30m over 3 years
    ALLOWABLE_DEFICIT = 5_000_000     # €5m acceptable loss per year
    
    def __init__(self):
        pass
    
    def calculate_three_year_loss(
        self,
        transactions: List[FinancialTransaction],
        current_date: date,
    ) -> int:
        """Calculate total loss over the last 3 years.
        
        Returns:
            Total loss (positive number = loss, negative = profit)
        """
        three_years_ago = current_date - timedelta(days=3*365)
        
        recent_transactions = [
            t for t in transactions
            if t.date >= three_years_ago and t.date <= current_date
        ]
        
        total_revenue = sum(
            t.amount for t in recent_transactions
            if t.category == "revenue"
        )
        total_expenses = sum(
            t.amount for t in recent_transactions
            if t.category == "expense"
        )
        
        loss = total_expenses - total_revenue
        return max(0, loss)  # Return 0 if profitable
    
    def check_compliance(
        self,
        three_year_loss: int,
        is_champions_league: bool = True,
    ) -> Tuple[bool, str]:
        """Check if club is FFP compliant.
        
        Returns:
            (is_compliant, message)
        """
        if three_year_loss <= self.MAX_THREE_YEAR_LOSS:
            return True, "FFP Compliant"
        
        excess = three_year_loss - self.MAX_THREE_YEAR_LOSS
        
        if excess < 10_000_000:
            return True, f"Warning: Near FFP limit (excess: €{excess:,})"
        else:
            if is_champions_league:
                return False, f"Non-compliant: €{excess:,} excess loss. Risk of European ban."
            else:
                return False, f"Non-compliant: €{excess:,} excess loss. Risk of sanctions."
    
    def get_potential_sanctions(
        self,
        three_year_loss: int,
        is_repeat_offender: bool = False,
    ) -> List[str]:
        """Get list of potential FFP sanctions."""
        sanctions = []
        
        if three_year_loss > self.MAX_THREE_YEAR_LOSS:
            sanctions.append("Fine: €20-50 million")
            sanctions.append("Squad size restriction (23 players max)")
            
            if three_year_loss > self.MAX_THREE_YEAR_LOSS * 1.5:
                sanctions.append("European competition ban")
            
            if is_repeat_offender:
                sanctions.append("Transfer ban (1-2 windows)")
                sanctions.append("Points deduction")
        
        return sanctions


class FinanceEngine:
    """Main finance engine for managing club finances."""
    
    def __init__(self):
        self.calculator = FinanceCalculator()
        self.ffp_calculator = FFPCalculator()
    
    def process_matchday(
        self,
        club_finances: ClubFinances,
        club: Club,
        is_home: bool,
        match_importance: str = "normal",  # normal, derby, title_race, cup
    ) -> int:
        """Process matchday revenue.
        
        Args:
            club_finances: Club's financial state
            club: Club data
            is_home: Whether club is playing at home
            match_importance: Importance factor for attendance
        
        Returns:
            Revenue generated
        """
        if not is_home:
            return 0  # No matchday revenue for away games
        
        # Determine attendance factors
        is_derby = match_importance == "derby"
        is_title_race = match_importance == "title_race"
        
        if match_importance == "cup":
            attendance_percent = 0.70  # Cup games usually lower attendance
        else:
            attendance_percent = 0.85
        
        revenue = self.calculator.calculate_matchday_revenue(
            club, attendance_percent, is_derby, is_title_race
        )
        
        # Record transaction
        transaction = FinancialTransaction(
            date=date.today(),
            amount=revenue,
            type=RevenueType.MATCHDAY,
            description=f"Matchday revenue ({match_importance})",
            category="revenue",
        )
        club_finances.add_transaction(transaction)
        
        return revenue
    
    def process_weekly_finances(
        self,
        club_finances: ClubFinances,
        club: Club,
        players: List[Player],
        week: date,
    ) -> WeeklyFinances:
        """Process all weekly financial transactions.
        
        Returns:
            Weekly financial summary
        """
        weekly = WeeklyFinances(week_start=week)
        
        # Expenses: Wages
        wage_bill = self.calculator.calculate_weekly_wage_bill(players)
        weekly.wage_bill = wage_bill
        
        transaction = FinancialTransaction(
            date=week,
            amount=wage_bill,
            type=ExpenseType.WAGES,
            description="Weekly player wages",
            category="expense",
        )
        club_finances.add_transaction(transaction)
        
        # Revenue: Commercial (sponsorships)
        commercial = self.calculator.calculate_commercial_revenue(club)
        weekly.commercial_revenue = commercial
        
        # Add commercial revenue (spread over season, so weekly)
        transaction = FinancialTransaction(
            date=week,
            amount=commercial,
            type=RevenueType.COMMERCIAL,
            description="Commercial revenue (sponsorships)",
            category="revenue",
        )
        club_finances.add_transaction(transaction)
        
        # Store weekly summary
        club_finances.weekly_history.append(weekly)
        
        return weekly
    
    def check_ffp_status(
        self,
        club_finances: ClubFinances,
        current_date: date,
    ) -> Tuple[bool, str, List[str]]:
        """Check FFP compliance status.
        
        Returns:
            (is_compliant, message, potential_sanctions)
        """
        three_year_loss = self.ffp_calculator.calculate_three_year_loss(
            club_finances.transactions,
            current_date,
        )
        
        club_finances.ffp_three_year_loss = three_year_loss
        
        is_compliant, message = self.ffp_calculator.check_compliance(three_year_loss)
        club_finances.ffp_compliant = is_compliant
        
        sanctions = self.ffp_calculator.get_potential_sanctions(three_year_loss)
        
        return is_compliant, message, sanctions


def format_money(amount: int) -> str:
    """Format money for display."""
    if amount >= 1_000_000_000:
        return f"€{amount/1_000_000_000:.2f}B"
    elif amount >= 1_000_000:
        return f"€{amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"€{amount/1_000:.0f}K"
    else:
        return f"€{amount}"
