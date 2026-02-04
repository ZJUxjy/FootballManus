#!/usr/bin/env python3
"""FM Manager Game Client - Main entry point for single-player and multiplayer modes.

This client provides:
- Single-player career mode
- Multiplayer online mode
- Complete season management
- Real-time match viewing
"""

import sys
import asyncio
import argparse
from pathlib import Path
from typing import Optional
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from colorama import Fore, Style, init as colorama_init

from fm_manager.core.database import init_db, get_session_maker
from fm_manager.core.save_load_enhanced import EnhancedSaveLoadManager, get_save_manager
from fm_manager.data.cleaned_data_loader import load_for_match_engine

# from fm_manager.engine.season_simulator import SeasonSimulator
from fm_manager.engine.match_engine_adapter import ClubSquadBuilder
from fm_manager.engine.finance_engine import FinanceEngine
from fm_manager.engine.transfer_engine import TransferEngine


class GameClient:
    """Main game client for FM Manager."""

    def __init__(self):
        colorama_init()
        self.db_session = None
        self.save_manager = get_save_manager()
        self.current_club = None
        self.current_season = 1
        self.current_week = 1
        self.in_game_date = date(2024, 8, 1)  # Season start

    def show_main_menu(self):
        """Display main menu."""
        print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'FM MANAGER 2024':^80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Main Menu:{Style.RESET_ALL}")
        print("  1. Start New Career")
        print("  2. Load Career")
        print("  3. Multiplayer")
        print("  4. Settings")
        print("  5. Exit")
        print()

    async def start_new_career(self):
        """Start a new single-player career."""
        print(f"\n{Fore.CYAN}Starting New Career{Style.RESET_ALL}\n")

        # Load clubs
        print("Loading clubs...")
        clubs, players = load_for_match_engine()

        # Filter major leagues
        major_leagues = [
            "England Premier League",
            "Spain La Liga",
            "Germany Bundesliga",
            "Italy Serie A",
        ]
        available_clubs = [c for c in clubs.values() if c.league in major_leagues]

        # Show club selection
        print(f"\n{Fore.GREEN}Select a club to manage:{Style.RESET_ALL}\n")

        for i, club in enumerate(available_clubs[:20], 1):
            budget = getattr(club, "balance", 0) or getattr(club, "transfer_budget", 0)
            print(f"{i:2d}. {club.name:<30} {club.league:<25} Budget: £{budget / 1_000_000:.1f}M")

        print(f"\n0. Back to main menu")

        while True:
            try:
                choice = input("\nSelect club (0-20): ").strip()
                if choice == "0":
                    return

                idx = int(choice) - 1
                if 0 <= idx < len(available_clubs[:20]):
                    self.current_club = available_clubs[idx]
                    break
                else:
                    print(f"{Fore.RED}Invalid selection{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Please enter a number{Style.RESET_ALL}")

        budget = getattr(self.current_club, "balance", 0) or getattr(
            self.current_club, "transfer_budget", 0
        )
        print(f"\n{Fore.GREEN}Welcome to {self.current_club.name}!{Style.RESET_ALL}")
        print(f"League: {self.current_club.league}")
        print(f"Budget: £{budget:,.0f}")
        print(f"Reputation: {self.current_club.reputation}")

        await self.run_career_mode()

    async def run_career_mode(self):
        """Main career mode loop."""
        while True:
            self.show_dashboard()

            print(f"\n{Fore.GREEN}What would you like to do?{Style.RESET_ALL}")
            print("  1. Squad Management")
            print("  2. Tactics")
            print("  3. Transfers")
            print("  4. Fixtures & Matches")
            print("  5. Youth Academy")
            print("  6. Finances")
            print("  7. Advance to Next Match")
            print("  8. Save Game")
            print("  9. Main Menu")
            print("  0. Exit Game")

            choice = input("\nChoice (0-9): ").strip()

            if choice == "1":
                await self.manage_squad()
            elif choice == "2":
                await self.manage_tactics()
            elif choice == "3":
                await self.manage_transfers()
            elif choice == "4":
                await self.view_fixtures()
            elif choice == "5":
                await self.manage_youth()
            elif choice == "6":
                await self.view_finances()
            elif choice == "7":
                await self.advance_matchday()
            elif choice == "8":
                await self.save_game()
            elif choice == "9":
                break
            elif choice == "0":
                await self.quit_game()
                break
            else:
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")

    def show_dashboard(self):
        """Display main dashboard."""
        print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{self.current_club.name:^80}{Style.RESET_ALL}")
        print(
            f"{Fore.CYAN}{f'Season {self.current_season}, Week {self.current_week} - {self.in_game_date}':^80}{Style.RESET_ALL}"
        )
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")

        # Show recent results (placeholder)
        print(f"{Fore.GREEN}Recent Results:{Style.RESET_ALL}")
        print("  Last 5: W-W-D-L-W")
        print("  League Position: #4")
        print("  Next Match: vs Arsenal (Home)\n")

        # Show news (placeholder)
        print(f"{Fore.GREEN}Latest News:{Style.RESET_ALL}")
        print("  - Star player returns from injury")
        print("  - Board pleased with recent form")
        print("  - Transfer window opens in 2 weeks\n")

    async def manage_squad(self):
        """Manage squad and lineups."""
        print(f"\n{Fore.CYAN}Squad Management{Style.RESET_ALL}\n")

        # Use players from ClubDataFull (loaded from CSV data)
        players = getattr(self.current_club, "players", [])

        print(f"{Fore.GREEN}Squad ({len(players)} players):{Style.RESET_ALL}\n")
        print(
            f"{'#':<4} {'Name':<25} {'Pos':<6} {'Age':<4} {'CA':<4} {'PA':<4} {'Form':<6} {'Fitness':<8}"
        )
        print("-" * 75)

        sorted_players = sorted(
            players, key=lambda p: getattr(p, "current_ability", 0), reverse=True
        )[:25]
        for i, player in enumerate(sorted_players, 1):
            form_str = (
                "★" * (getattr(player, "form", 0) // 20) if getattr(player, "form", 0) else "-"
            )
            fitness_str = (
                f"{getattr(player, 'fitness', 0)}%" if getattr(player, "fitness", 0) else "-"
            )
            position = getattr(player, "position", None)
            # Handle both enum and string positions
            if hasattr(position, "value"):
                position_str = position.value
            elif isinstance(position, str):
                position_str = position
            else:
                position_str = "-"

            print(
                f"{i:<4} {getattr(player, 'full_name', 'Unknown')[:24]:<25} {position_str:<6} "
                f"{getattr(player, 'age', '-'):<4} {getattr(player, 'current_ability', '-'):<4} "
                f"{getattr(player, 'potential_ability', '-'):<4} "
                f"{form_str:<6} {fitness_str:<8}"
            )

        print(f"\n{Fore.YELLOW}Options:{Style.RESET_ALL}")
        print("  1. View Player Details")
        print("  0. Back to Dashboard")

        choice = input("\nChoice (0-1): ").strip()

        if choice == "1":
            try:
                player_idx = int(input("Enter player number to view details: ").strip()) - 1
                if 0 <= player_idx < len(sorted_players):
                    await self.view_player_detail(sorted_players[player_idx])
                else:
                    print(f"{Fore.RED}Invalid player number{Style.RESET_ALL}")
                    input("\nPress Enter to continue...")
            except ValueError:
                print(f"{Fore.RED}Invalid input{Style.RESET_ALL}")
                input("\nPress Enter to continue...")

    async def view_player_detail(self, player):
        """View detailed player information."""
        print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{getattr(player, 'full_name', 'Unknown'):^80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")

        # Basic Info
        print(f"{Fore.GREEN}Basic Information:{Style.RESET_ALL}")
        position = getattr(player, "position", "-")
        pos_str = position if isinstance(position, str) else getattr(position, "value", "-")
        print(f"  Position: {pos_str}")
        print(f"  Age: {getattr(player, 'age', '-')}")
        print(f"  Nationality: {getattr(player, 'nationality', '-')}")
        print(f"  Club: {getattr(self.current_club, 'name', '-')}")

        # Abilities
        print(f"\n{Fore.GREEN}Abilities:{Style.RESET_ALL}")
        ca = getattr(player, "current_ability", 0)
        pa = getattr(player, "potential_ability", 0)
        print(f"  Current Ability (CA): {ca}")
        print(f"  Potential Ability (PA): {pa}")

        # Contract Info
        print(f"\n{Fore.GREEN}Contract & Value:{Style.RESET_ALL}")
        market_value = getattr(player, "market_value", 0)
        weekly_wage = getattr(player, "weekly_wage", 0)
        print(f"  Market Value: £{market_value:,.0f}")
        print(f"  Weekly Wage: £{weekly_wage:,.0f}")

        # Status
        print(f"\n{Fore.GREEN}Status:{Style.RESET_ALL}")
        fatigue = getattr(player, "fatigue", 0)
        stamina = getattr(player, "stamina", 0)
        match_shape = getattr(player, "match_shape", 0)
        happiness = getattr(player, "happiness", 0)
        print(f"  Fatigue: {fatigue}%")
        print(f"  Stamina: {stamina}%")
        print(f"  Match Shape: {match_shape}%")
        print(f"  Happiness: {happiness}%")

        # Position Ratings (if available)
        print(f"\n{Fore.GREEN}Position Ratings:{Style.RESET_ALL}")
        pos_ratings = getattr(player, "position_ratings", None)
        if pos_ratings:
            if isinstance(pos_ratings, dict):
                for pos, rating in pos_ratings.items():
                    print(f"  {pos}: {rating}")
            else:
                print(f"  {pos_ratings}")
        else:
            print(f"  {Fore.YELLOW}Position ratings not available{Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        input("\nPress Enter to continue...")

    async def manage_tactics(self):
        """Manage tactics and formation."""
        print(f"\n{Fore.CYAN}Tactics{Style.RESET_ALL}\n")

        formations = ["4-3-3", "4-4-2", "3-5-2", "4-2-3-1", "5-3-2", "4-1-4-1"]

        print(f"{Fore.GREEN}Current Formation:{Style.RESET_ALL} 4-3-3")
        print(f"\n{Fore.GREEN}Available Formations:{Style.RESET_ALL}")
        for i, formation in enumerate(formations, 1):
            print(f"  {i}. {formation}")

        print(f"\n{Fore.YELLOW}Tactical Styles:{Style.RESET_ALL}")
        styles = ["Tiki-Taka", "Gegenpressing", "Counter-Attack", "Long Ball", "Park the Bus"]
        for i, style in enumerate(styles, 1):
            print(f"  {i}. {style}")

        input("\nPress Enter to continue...")

    async def manage_transfers(self):
        """Manage transfers - buy and sell players."""
        while True:
            print(f"\n{Fore.CYAN}Transfer Center{Style.RESET_ALL}\n")

            budget = getattr(self.current_club, "transfer_budget", 0) or getattr(
                self.current_club, "balance", 0
            )
            print(f"{Fore.GREEN}Transfer Budget:{Style.RESET_ALL} £{budget:,.0f}")
            wage_budget = getattr(self.current_club, "wage_budget", 0)
            print(f"{Fore.GREEN}Wage Budget:{Style.RESET_ALL} £{wage_budget:,.0f}/week\n")

            print(f"{Fore.YELLOW}Transfer Options:{Style.RESET_ALL}")
            print("  1. Search Players to Buy")
            print("  2. View My Squad (Sell Players)")
            print("  3. Incoming Transfer Offers")
            print("  4. Transfer History")
            print("  0. Back to Dashboard")

            choice = input("\nChoice (0-4): ").strip()

            if choice == "1":
                await self.search_players_to_buy()
            elif choice == "2":
                await self.sell_players()
            elif choice == "3":
                await self.view_incoming_offers()
            elif choice == "4":
                await self.view_transfer_history()
            elif choice == "0":
                break
            else:
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")

    async def search_players_to_buy(self):
        """Search for players to buy from other clubs."""
        print(f"\n{Fore.CYAN}Player Search{Style.RESET_ALL}\n")

        # Get all players from loaded data (excluding current club)
        all_clubs, all_players = load_for_match_engine()

        print("Search by:")
        print("  1. Position")
        print("  2. Minimum Ability")
        print("  3. Maximum Price")
        print("  4. View All Available")
        print("  0. Back")

        choice = input("\nChoice (0-4): ").strip()

        filtered_players = []

        if choice == "1":
            position = input("Enter position (GK/CB/LB/RB/DM/CM/CAM/LW/RW/ST): ").strip().upper()
            for player in all_players.values():
                player_pos = getattr(player, "position", "")
                pos_str = (
                    player_pos if isinstance(player_pos, str) else getattr(player_pos, "value", "")
                )
                if position in pos_str.upper():
                    # Exclude players from current club
                    player_club_id = getattr(player, "club_id", -1)
                    current_club_id = getattr(self.current_club, "id", -2)
                    if player_club_id != current_club_id and player_club_id > 0:
                        filtered_players.append(player)

        elif choice == "2":
            try:
                min_ca = int(input("Minimum Current Ability (50-100): ").strip())
                for player in all_players.values():
                    ca = getattr(player, "current_ability", 0)
                    if ca >= min_ca:
                        player_club_id = getattr(player, "club_id", -1)
                        current_club_id = getattr(self.current_club, "id", -2)
                        if player_club_id != current_club_id and player_club_id > 0:
                            filtered_players.append(player)
            except ValueError:
                print(f"{Fore.RED}Invalid number{Style.RESET_ALL}")
                return

        elif choice == "3":
            try:
                max_price = int(input("Maximum Price (in millions): ").strip()) * 1_000_000
                for player in all_players.values():
                    value = getattr(player, "value", 0) or getattr(
                        player, "estimated_value", 1000000
                    )
                    if value <= max_price:
                        player_club_id = getattr(player, "club_id", -1)
                        current_club_id = getattr(self.current_club, "id", -2)
                        if player_club_id != current_club_id and player_club_id > 0:
                            filtered_players.append(player)
            except ValueError:
                print(f"{Fore.RED}Invalid number{Style.RESET_ALL}")
                return

        elif choice == "4":
            for player in all_players.values():
                player_club_id = getattr(player, "club_id", -1)
                current_club_id = getattr(self.current_club, "id", -2)
                if player_club_id != current_club_id and player_club_id > 0:
                    filtered_players.append(player)

        elif choice == "0":
            return

        # Sort by ability and show top 20
        filtered_players = sorted(
            filtered_players, key=lambda p: getattr(p, "current_ability", 0), reverse=True
        )[:20]

        if not filtered_players:
            print(f"\n{Fore.YELLOW}No players found matching your criteria.{Style.RESET_ALL}")
            input("\nPress Enter to continue...")
            return

        print(f"\n{Fore.GREEN}Found {len(filtered_players)} players:{Style.RESET_ALL}\n")
        print(
            f"{'#':<4} {'Name':<25} {'Pos':<6} {'Age':<4} {'CA':<4} {'PA':<4} {'Value':<12} {'Club':<20}"
        )
        print("-" * 85)

        for i, player in enumerate(filtered_players, 1):
            name = getattr(player, "full_name", "Unknown")[:24]
            pos = getattr(player, "position", "-")
            pos_str = pos if isinstance(pos, str) else getattr(pos, "value", "-")
            age = getattr(player, "age", "-")
            ca = getattr(player, "current_ability", "-")
            pa = getattr(player, "potential_ability", "-")
            value = getattr(player, "market_value", 0)

            # Find club name
            club_name = "Unknown"
            club_id = getattr(player, "club_id", None)
            if club_id and club_id in all_clubs:
                club_name = getattr(all_clubs[club_id], "name", "Unknown")[:19]

            print(
                f"{i:<4} {name:<25} {pos_str:<6} {age:<4} {ca:<4} {pa:<4} £{value / 1_000_000:.1f}M{'':<5} {club_name:<20}"
            )

        print(
            f"\n{Fore.YELLOW}Enter player number to make an offer (0 to go back):{Style.RESET_ALL}"
        )
        try:
            player_choice = int(input("Choice: ").strip())
            if player_choice > 0 and player_choice <= len(filtered_players):
                await self.make_transfer_offer(filtered_players[player_choice - 1])
        except ValueError:
            pass

    async def make_transfer_offer(self, player):
        """Make a transfer offer for a player."""
        print(f"\n{Fore.CYAN}Make Transfer Offer{Style.RESET_ALL}\n")

        player_name = getattr(player, "full_name", "Unknown")
        print(f"Player: {Fore.GREEN}{player_name}{Style.RESET_ALL}")

        current_value = getattr(player, "market_value", 0)
        print(f"Estimated Value: £{current_value:,.0f}")

        print(f"\n{Fore.YELLOW}Offer Type:{Style.RESET_ALL}")
        print("  1. Transfer Fee (Permanent)")
        print("  2. Loan")
        print("  0. Cancel")

        choice = input("\nChoice (0-2): ").strip()

        if choice == "1":
            try:
                offer_amount = (
                    int(
                        input(
                            f"Enter offer amount (in millions, value is £{current_value / 1_000_000:.1f}M): "
                        ).strip()
                    )
                    * 1_000_000
                )

                budget = getattr(self.current_club, "transfer_budget", 0) or getattr(
                    self.current_club, "balance", 0
                )
                if offer_amount > budget:
                    print(
                        f"\n{Fore.RED}Error: Offer exceeds your transfer budget!{Style.RESET_ALL}"
                    )
                    input("\nPress Enter to continue...")
                    return

                print(f"\n{Fore.GREEN}Transfer offer submitted!{Style.RESET_ALL}")
                print(f"Offer: £{offer_amount:,.0f} for {player_name}")
                print(
                    f"\n{Fore.YELLOW}Note: This is a simplified transfer system.{Style.RESET_ALL}"
                )
                print("In a full implementation, the other club would respond to your offer.")

            except ValueError:
                print(f"{Fore.RED}Invalid amount{Style.RESET_ALL}")

        elif choice == "2":
            try:
                loan_fee = int(input("Enter monthly loan fee (in thousands): ").strip()) * 1000
                wage_split = int(input("Percentage of wages you'll pay (0-100): ").strip())

                print(f"\n{Fore.GREEN}Loan offer submitted!{Style.RESET_ALL}")
                print(f"Monthly Fee: £{loan_fee:,.0f}, Wage Split: {wage_split}%")

            except ValueError:
                print(f"{Fore.RED}Invalid input{Style.RESET_ALL}")

        input("\nPress Enter to continue...")

    async def sell_players(self):
        """List your own players for sale or accept offers."""
        print(f"\n{Fore.CYAN}My Squad - Sell Players{Style.RESET_ALL}\n")

        # Get current club players
        players = getattr(self.current_club, "players", [])

        if not players:
            print(f"{Fore.YELLOW}No players in your squad.{Style.RESET_ALL}")
            input("\nPress Enter to continue...")
            return

        # Sort by value
        sorted_players = sorted(
            players,
            key=lambda p: getattr(p, "value", 0) or getattr(p, "estimated_value", 0),
            reverse=True,
        )

        print(f"{Fore.GREEN}Your Squad ({len(players)} players):{Style.RESET_ALL}\n")
        print(f"{'#':<4} {'Name':<25} {'Pos':<6} {'Age':<4} {'CA':<4} {'Value':<12} {'Status':<15}")
        print("-" * 75)

        for i, player in enumerate(sorted_players[:25], 1):
            name = getattr(player, "full_name", "Unknown")[:24]
            pos = getattr(player, "position", "-")
            pos_str = pos if isinstance(pos, str) else getattr(pos, "value", "-")
            age = getattr(player, "age", "-")
            ca = getattr(player, "current_ability", "-")
            value = getattr(player, "market_value", 0)
            status = "For Sale" if getattr(player, "is_listed", False) else "Not Listed"

            print(
                f"{i:<4} {name:<25} {pos_str:<6} {age:<4} {ca:<4} £{value / 1_000_000:.1f}M{'':<5} {status:<15}"
            )

        print(f"\n{Fore.YELLOW}Options:{Style.RESET_ALL}")
        print("  1. List Player for Sale")
        print("  2. Remove from Transfer List")
        print("  3. Set Asking Price")
        print("  0. Back")

        choice = input("\nChoice (0-3): ").strip()

        if choice == "1":
            try:
                player_idx = int(input("Enter player number to list: ").strip()) - 1
                if 0 <= player_idx < len(sorted_players):
                    player = sorted_players[player_idx]
                    asking_price = (
                        int(input(f"Enter asking price (in millions): ").strip()) * 1_000_000
                    )

                    # In a real implementation, this would update the database
                    print(
                        f"\n{Fore.GREEN}{getattr(player, 'full_name', 'Player')} listed for sale!{Style.RESET_ALL}"
                    )
                    print(f"Asking Price: £{asking_price:,.0f}")
                else:
                    print(f"{Fore.RED}Invalid player number{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Invalid input{Style.RESET_ALL}")

        elif choice == "2":
            print(f"\n{Fore.YELLOW}Player removed from transfer list.{Style.RESET_ALL}")

        elif choice == "3":
            print(f"\n{Fore.YELLOW}Asking price updated.{Style.RESET_ALL}")

        input("\nPress Enter to continue...")

    async def view_incoming_offers(self):
        """View and respond to incoming transfer offers."""
        print(f"\n{Fore.CYAN}Incoming Transfer Offers{Style.RESET_ALL}\n")

        # This would query the database for actual offers
        # For now, show placeholder
        print(f"{Fore.YELLOW}No incoming offers at this time.{Style.RESET_ALL}")
        print("\nWhen other clubs make offers for your players, they will appear here.")
        print("You can then:")
        print("  - Accept the offer")
        print("  - Reject the offer")
        print("  - Negotiate (counter-offer)")

        input("\nPress Enter to continue...")

    async def view_transfer_history(self):
        """View recent transfer activity."""
        print(f"\n{Fore.CYAN}Transfer History{Style.RESET_ALL}\n")

        print(f"{Fore.YELLOW}Recent Transfers:{Style.RESET_ALL}")
        print("  No recent transfers to display.")
        print("\nThis would show:")
        print("  - Players you've bought")
        print("  - Players you've sold")
        print("  - Transfer fees paid/received")

        input("\nPress Enter to continue...")

    async def view_fixtures(self):
        """View fixtures and results."""
        print(f"\n{Fore.CYAN}Fixtures & Results{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Upcoming Matches:{Style.RESET_ALL}")
        print("  Week 15: vs Arsenal (H)")
        print("  Week 16: vs Chelsea (A)")
        print("  Week 17: vs Liverpool (H)")
        print("  Week 18: vs Man City (A)")

        print(f"\n{Fore.GREEN}Recent Results:{Style.RESET_ALL}")
        print("  Week 14: Tottenham 2-1 (W)")
        print("  Week 13: Everton 0-0 (D)")
        print("  Week 12: Brighton 3-2 (W)")

        input("\nPress Enter to continue...")

    async def manage_youth(self):
        """Manage youth academy."""
        print(f"\n{Fore.CYAN}Youth Academy{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Academy Status:{Style.RESET_ALL} Excellent")
        print(f"{Fore.GREEN}Youth Players:{Style.RESET_ALL} 24")
        print(f"{Fore.GREEN}Potential Stars:{Style.RESET_ALL} 3\n")

        print("Top Prospects:")
        print("  1. James Wilson (ST, 17) - PA: 85")
        print("  2. Tom Davies (CM, 16) - PA: 82")
        print("  3. Alex Johnson (CB, 17) - PA: 78")

        input("\nPress Enter to continue...")

    async def view_finances(self):
        """View financial status."""
        print(f"\n{Fore.CYAN}Finances{Style.RESET_ALL}\n")

        balance = getattr(self.current_club, "balance", 0)
        transfer_budget = getattr(self.current_club, "transfer_budget", 0)
        wage_budget = getattr(self.current_club, "wage_budget", 0)

        print(f"{Fore.GREEN}Current Balance:{Style.RESET_ALL} £{balance:,.0f}")
        print(f"{Fore.GREEN}Transfer Budget:{Style.RESET_ALL} £{transfer_budget:,.0f}")
        print(f"{Fore.GREEN}Wage Budget:{Style.RESET_ALL} £{wage_budget:,.0f}/week\n")

        print(f"{Fore.GREEN}Season Income (Projected):{Style.RESET_ALL}")
        print("  Match Day: £25M")
        print("  TV Rights: £100M")
        print("  Commercial: £30M")

        input("\nPress Enter to continue...")

    async def advance_matchday(self):
        """Advance to next matchday."""
        print(f"\n{Fore.CYAN}Advancing to Next Match...{Style.RESET_ALL}\n")

        # Simulate a match (placeholder)
        print("Simulating match vs Arsenal...")
        print("Match Result: 2-1 Win!")
        print("Goalscorers: Smith (34'), Johnson (67')")

        self.current_week += 1
        self.in_game_date = date(
            self.in_game_date.year, self.in_game_date.month, self.in_game_date.day + 7
        )

        input("\nPress Enter to continue...")

    async def quit_game(self):
        """Quit the game with confirmation."""
        print(f"\n{Fore.YELLOW}Are you sure you want to exit?{Style.RESET_ALL}")
        print("  1. Save and Exit")
        print("  2. Exit without Saving")
        print("  3. Cancel")

        choice = input("\nChoice (1-3): ").strip()

        if choice == "1":
            await self.save_game()
            print(f"\n{Fore.GREEN}Thanks for playing FM Manager!{Style.RESET_ALL}\n")
        elif choice == "2":
            print(f"\n{Fore.GREEN}Thanks for playing FM Manager!{Style.RESET_ALL}\n")
        elif choice == "3":
            print(f"\n{Fore.CYAN}Returning to game...{Style.RESET_ALL}")

    async def save_game(self):
        """Save current game."""
        print(f"\n{Fore.CYAN}Save Game{Style.RESET_ALL}\n")

        save_name = input("Enter save name (or press Enter for auto-name): ").strip()

        if not save_name:
            save_name = f"{self.current_club.name}_S{self.current_season}W{self.current_week}"

        try:
            save_path = await self.save_manager.save_game_async(
                session=self.db_session,
                save_name=save_name,
                current_season=self.current_season,
                current_week=self.current_week,
                player_club_id=self.current_club.id,
                in_game_date=self.in_game_date,
            )
            print(f"{Fore.GREEN}✓ Game saved: {save_path}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error saving game: {e}{Style.RESET_ALL}")

        input("\nPress Enter to continue...")

    async def load_career(self):
        """Load an existing career."""
        print(f"\n{Fore.CYAN}Load Career{Style.RESET_ALL}\n")

        saves = self.save_manager.get_save_files()

        if not saves:
            print(f"{Fore.YELLOW}No save files found.{Style.RESET_ALL}")
            input("\nPress Enter to continue...")
            return

        print(f"{Fore.GREEN}Available Saves:{Style.RESET_ALL}\n")

        for i, (metadata, path) in enumerate(saves[:10], 1):
            date_str = metadata.save_date.strftime("%Y-%m-%d %H:%M")
            print(
                f"{i}. {metadata.save_name:<30} {date_str}  "
                f"S{metadata.current_season}W{metadata.current_week}"
            )

        print("\n0. Back to main menu")

        try:
            choice = input("\nSelect save (0-10): ").strip()
            if choice == "0":
                return

            idx = int(choice) - 1
            if 0 <= idx < len(saves[:10]):
                metadata, path = saves[idx]
                print(f"\n{Fore.GREEN}Loading {metadata.save_name}...{Style.RESET_ALL}")

                # Load game state
                loaded_metadata, game_state = self.save_manager.load_game(metadata.save_name)

                # Restore to database
                await self.save_manager.restore_game_state_async(self.db_session, game_state)

                # Update client state
                self.current_season = loaded_metadata.current_season
                self.current_week = loaded_metadata.current_week
                if loaded_metadata.in_game_date:
                    self.in_game_date = loaded_metadata.in_game_date

                # Load current club from CSV data (avoiding database enum issues)
                if loaded_metadata.player_club_id:
                    clubs, _ = load_for_match_engine()
                    if loaded_metadata.player_club_id in clubs:
                        self.current_club = clubs[loaded_metadata.player_club_id]
                    else:
                        # Fallback: try to find by name
                        for club in clubs.values():
                            if club.name == loaded_metadata.player_club_name:
                                self.current_club = club
                                break

                print(f"{Fore.GREEN}✓ Game loaded successfully!{Style.RESET_ALL}")
                input("\nPress Enter to continue...")

                # Start career mode
                await self.run_career_mode()
            else:
                print(f"{Fore.RED}Invalid selection{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error loading game: {e}{Style.RESET_ALL}")
            input("\nPress Enter to continue...")

    async def multiplayer_mode(self):
        """Start multiplayer mode."""
        print(f"\n{Fore.CYAN}Multiplayer Mode{Style.RESET_ALL}\n")

        print("Options:")
        print("  1. Create Room")
        print("  2. Join Room")
        print("  3. Back")

        choice = input("\nChoice (1-3): ").strip()

        if choice == "1":
            print("\nStarting server...")
            print(f"{Fore.YELLOW}To create a room, run:{Style.RESET_ALL}")
            print("  python -m fm_manager.server.main")
            print("\nThen connect with other players.")
        elif choice == "2":
            room_id = input("Enter room ID: ").strip()
            print(f"\nConnecting to room {room_id}...")
            print(f"{Fore.YELLOW}Multiplayer client coming soon!{Style.RESET_ALL}")

        input("\nPress Enter to continue...")

    async def settings(self):
        """Game settings."""
        print(f"\n{Fore.CYAN}Settings{Style.RESET_ALL}\n")

        print("Options:")
        print("  1. Match Speed")
        print("  2. Auto-Save")
        print("  3. Sound")
        print("  4. Back")

        input("\nPress Enter to continue...")

    async def run_async(self):
        """Async main game loop."""
        await init_db()
        session_maker = get_session_maker()
        async with session_maker() as session:
            self.db_session = session
            while True:
                self.show_main_menu()
                choice = input("Select option (1-5): ").strip()
                if choice == "1":
                    await self.start_new_career()
                elif choice == "2":
                    await self.load_career()
                elif choice == "3":
                    await self.multiplayer_mode()
                elif choice == "4":
                    await self.settings()
                elif choice == "5":
                    print(f"\n{Fore.GREEN}Thanks for playing FM Manager!{Style.RESET_ALL}\n")
                    break
                else:
                    print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="FM Manager Game Client")
    parser.add_argument(
        "--quick-start", action="store_true", help="Skip menu and start new career immediately"
    )
    parser.add_argument("--club", type=str, help="Club name for quick start")

    args = parser.parse_args()

    client = GameClient()

    if args.quick_start:
        # Quick start with default club
        asyncio.run(client.start_new_career())
    else:
        asyncio.run(client.run_async())


if __name__ == "__main__":
    main()
