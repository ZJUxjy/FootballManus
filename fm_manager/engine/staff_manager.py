"""Staff manager for FM Manager.

Handles all staff-related operations including hiring, firing,
effect calculations, and staff candidate generation.
"""

import random
from datetime import date, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass

from fm_manager.core.models.staff import Staff, StaffRole, StaffEffect


# First name pools by nationality for candidate generation
FIRST_NAMES = {
    "England": ["James", "William", "John", "Thomas", "George", "Harry", "Oliver", "Jack", "Charlie", "Jacob"],
    "Spain": ["Antonio", "Jose", "Manuel", "Francisco", "David", "Juan", "Javier", "Daniel", "Carlos", "Miguel"],
    "Germany": ["Max", "Paul", "Ben", "Finn", "Noah", "Leon", "Elias", "Louis", "Felix", "Henry"],
    "Italy": ["Leonardo", "Francesco", "Alessandro", "Lorenzo", "Mattia", "Andrea", "Gabriele", "Riccardo", "Tommaso", "Edoardo"],
    "France": ["Gabriel", "Leo", "Raphael", "Louis", "Arthur", "Jules", "Adam", "Lucas", "Hugo", "Noah"],
    "Brazil": ["Miguel", "Arthur", "Gael", "Heitor", "Theo", "Davi", "Ravi", "Guilherme", "Bernardo", "Noah"],
    "Argentina": ["Mateo", "Bautista", "Juan", "Felipe", "Bruno", "Noah", "Benicio", "Liam", "Thiago", "Ciro"],
    "Netherlands": ["Noah", "Sem", "Luca", "Levi", "James", "Milan", "Daan", "Noud", "Luuk", "Lars"],
    "Portugal": ["Francisco", "Afonso", "Santiago", "Tomas", "Miguel", "Duarte", "Gabriel", "Lourenco", "Goncalo", "Diogo"],
    "Default": ["Alex", "Michael", "David", "Chris", "John", "Robert", "Daniel", "Paul", "Mark", "Andrew"],
}

LAST_NAMES = {
    "England": ["Smith", "Jones", "Williams", "Brown", "Taylor", "Davies", "Wilson", "Evans", "Thomas", "Johnson"],
    "Spain": ["Garcia", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Ramirez", "Torres"],
    "Germany": ["Muller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Hoffmann", "Schulz"],
    "Italy": ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo", "Ricci", "Marino", "Greco"],
    "France": ["Martin", "Bernard", "Thomas", "Petit", "Robert", "Richard", "Durand", "Dubois", "Moreau", "Laurent"],
    "Brazil": ["Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", "Pereira", "Lima", "Gomes"],
    "Argentina": ["Gonzalez", "Rodriguez", "Gomez", "Fernandez", "Lopez", "Martinez", "Sanchez", "Perez", "Garcia", "Romero"],
    "Netherlands": ["De Jong", "Jansen", "De Vries", "Van den Berg", "Van Dijk", "Bakker", "Janssen", "Visser", "Smit", "Meijer"],
    "Portugal": ["Silva", "Santos", "Ferreira", "Costa", "Pereira", "Martins", "Rodrigues", "Almeida", "Ribeiro", "Carvalho"],
    "Default": ["Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson", "Martinez"],
}


@dataclass
class StaffCandidate:
    """A candidate for a staff position."""
    staff: Staff
    asking_salary: int
    contract_length_years: int


class StaffManager:
    """Manages staff operations for a club."""
    
    # Salary calculation constants
    MIN_ABILITY = 50
    MAX_ABILITY = 95
    MIN_SALARY = 1000
    MAX_SALARY = 150000
    
    def __init__(self, club_id: Optional[int] = None):
        """Initialize staff manager.
        
        Args:
            club_id: Optional club ID to manage staff for
        """
        self.club_id = club_id
        self._staff_cache: Dict[int, List[Staff]] = {}
    
    def get_staff_by_role(
        self, 
        staff_list: List[Staff], 
        role: StaffRole
    ) -> List[Staff]:
        """Get all staff members with a specific role.
        
        Args:
            staff_list: List of staff to filter
            role: Role to filter by
            
        Returns:
            List of staff with the specified role
        """
        return [s for s in staff_list if s.role == role]
    
    def get_head_coach(self, staff_list: List[Staff]) -> Optional[Staff]:
        """Get the head coach from a staff list.
        
        Args:
            staff_list: List of staff to search
            
        Returns:
            Head coach if found, None otherwise
        """
        coaches = self.get_staff_by_role(staff_list, StaffRole.HEAD_COACH)
        return coaches[0] if coaches else None
    
    def hire_staff(
        self,
        staff: Staff,
        club_id: int,
        salary: int,
        contract_years: int = 2,
    ) -> bool:
        """Hire a staff member to a club.
        
        Args:
            staff: Staff member to hire
            club_id: ID of the hiring club
            salary: Weekly salary offered
            contract_years: Contract length in years
            
        Returns:
            True if successful
        """
        if staff.is_hired:
            return False
        
        contract_until = date.today() + timedelta(days=365 * contract_years)
        
        staff.club_id = club_id
        staff.salary = salary
        staff.contract_until = contract_until
        staff.is_hired = True
        
        return True
    
    def fire_staff(
        self,
        staff: Staff,
        compensation: Optional[int] = None,
    ) -> int:
        """Fire a staff member.
        
        Args:
            staff: Staff member to fire
            compensation: Optional compensation amount (if None, calculates automatically)
            
        Returns:
            Compensation amount paid
        """
        if not staff.is_hired:
            return 0
        
        # Calculate compensation if not provided
        if compensation is None:
            # Typically 3-6 months salary as compensation
            months_remaining = staff.contract_years_remaining * 12
            compensation_months = min(6, max(3, months_remaining))
            compensation = staff.salary * 4 * compensation_months  # 4 weeks per month
        
        # Clear employment
        staff.club_id = None
        staff.is_hired = False
        staff.contract_until = None
        
        return compensation
    
    def calculate_staff_effects(self, staff_list: List[Staff]) -> StaffEffect:
        """Calculate combined effects from all staff.
        
        Args:
            staff_list: List of staff members
            
        Returns:
            Combined staff effects
        """
        combined = StaffEffect()
        
        for staff in staff_list:
            if staff.is_hired:
                effect = staff.calculate_effect()
                combined = combined.combine(effect)
        
        return combined
    
    def get_total_weekly_wages(self, staff_list: List[Staff]) -> int:
        """Calculate total weekly wages for all staff.
        
        Args:
            staff_list: List of staff members
            
        Returns:
            Total weekly wages
        """
        return sum(s.salary for s in staff_list if s.is_hired)
    
    def calculate_salary_for_ability(self, ability: int) -> int:
        """Calculate appropriate salary based on ability.
        
        Salary range: 1,000/周 (ability 50) to 150,000/周 (ability 95+)
        
        Args:
            ability: Staff ability (0-100)
            
        Returns:
            Weekly salary
        """
        ability = max(self.MIN_ABILITY, min(100, ability))
        
        if ability < self.MIN_ABILITY:
            return self.MIN_SALARY
        
        if ability >= self.MAX_ABILITY:
            return self.MAX_SALARY
        
        # Exponential growth for higher abilities
        # 50 -> 1000, 95+ -> 150000
        ability_range = self.MAX_ABILITY - self.MIN_ABILITY
        salary_range = self.MAX_SALARY - self.MIN_SALARY
        
        # Non-linear scaling: higher abilities get disproportionately higher salaries
        normalized = (ability - self.MIN_ABILITY) / ability_range
        scaled = normalized ** 2.5  # Exponential curve
        
        return int(self.MIN_SALARY + scaled * salary_range)
    
    def generate_staff_candidate(
        self,
        role: StaffRole,
        min_ability: int = 50,
        max_ability: int = 90,
        nationality: Optional[str] = None,
    ) -> StaffCandidate:
        """Generate a random staff candidate.
        
        Args:
            role: Staff role
            min_ability: Minimum ability (0-100)
            max_ability: Maximum ability (0-100)
            nationality: Optional specific nationality
            
        Returns:
            Staff candidate with asking salary and contract terms
        """
        # Generate random ability within range
        ability = random.randint(min_ability, max_ability)
        
        # Generate name
        if nationality is None:
            nationality = random.choice(list(FIRST_NAMES.keys())[:-1])  # Exclude Default
        
        first_names = FIRST_NAMES.get(nationality, FIRST_NAMES["Default"])
        last_names = LAST_NAMES.get(nationality, LAST_NAMES["Default"])
        
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        
        # Generate birth date (staff are typically 35-65 years old)
        age = random.randint(35, 65)
        birth_year = date.today().year - age
        birth_date = date(
            birth_year,
            random.randint(1, 12),
            random.randint(1, 28)
        )
        
        # Calculate salary expectation
        asking_salary = self.calculate_salary_for_ability(ability)
        
        # Slight random variation (±10%)
        variation = random.uniform(0.9, 1.1)
        asking_salary = int(asking_salary * variation)
        
        # Generate contract length (1-3 years)
        contract_years = random.randint(1, 3)
        
        # Calculate reputation based on ability
        reputation = ability * 100 + random.randint(-500, 500)
        reputation = max(500, min(10000, reputation))
        
        staff = Staff(
            id=0,  # Will be assigned by database
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            nationality=nationality,
            role=role,
            ability=ability,
            reputation=reputation,
            club_id=None,
            contract_until=None,
            salary=asking_salary,
            has_release_clause=False,
            release_clause_amount=None,
            is_hired=False,
        )
        
        return StaffCandidate(
            staff=staff,
            asking_salary=asking_salary,
            contract_length_years=contract_years,
        )
    
    def generate_candidate_pool(
        self,
        role: StaffRole,
        count: int = 5,
        min_ability: int = 50,
        max_ability: int = 90,
    ) -> List[StaffCandidate]:
        """Generate a pool of staff candidates.
        
        Args:
            role: Staff role
            count: Number of candidates to generate
            min_ability: Minimum ability
            max_ability: Maximum ability
            
        Returns:
            List of staff candidates
        """
        candidates = []
        for _ in range(count):
            candidate = self.generate_staff_candidate(
                role=role,
                min_ability=min_ability,
                max_ability=max_ability,
            )
            candidates.append(candidate)
        
        # Sort by ability (highest first)
        candidates.sort(key=lambda c: c.staff.ability, reverse=True)
        return candidates
    
    def get_role_description(self, role: StaffRole) -> str:
        """Get description of what a staff role does.
        
        Args:
            role: Staff role
            
        Returns:
            Description of the role
        """
        descriptions = {
            StaffRole.HEAD_COACH: 
                "Responsible for overall player development and match preparation.",
            StaffRole.ASSISTANT_MANAGER: 
                "Supports the head coach and helps maintain team morale.",
            StaffRole.GOALKEEPER_COACH: 
                "Specializes in training and developing goalkeepers.",
            StaffRole.FITNESS_COACH: 
                "Manages player fitness and helps prevent injuries.",
            StaffRole.CHIEF_SCOUT: 
                "Leads scouting operations to find new talent.",
            StaffRole.HEAD_PHYSIO: 
                "Manages medical staff and oversees injury recovery.",
        }
        return descriptions.get(role, "Unknown role")
    
    def can_afford_staff(
        self,
        weekly_budget: int,
        current_staff_wages: int,
        candidate_salary: int,
    ) -> bool:
        """Check if a club can afford to hire a staff member.
        
        Args:
            weekly_budget: Available weekly budget for staff wages
            current_staff_wages: Current total staff wages
            candidate_salary: Salary of candidate
            
        Returns:
            True if affordable
        """
        total_wages = current_staff_wages + candidate_salary
        return total_wages <= weekly_budget
