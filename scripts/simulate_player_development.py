#!/usr/bin/env python3
"""球员成长系统模拟程序

展示球员成长系统的功能：
- 青训球员生成
- 球员成长曲线
- 年龄相关的能力变化
- 伤病后的恢复和影响
- 球员退役
"""

import sys
import random
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.engine.player_development import (
    PlayerDevelopmentEngine,
    YouthAcademyGenerator,
    DevelopmentTracker,
    YouthIntakeConfig,
    DevelopmentPhase,
)
from fm_manager.core.models import Player, Position
from colorama import Fore, Style, init as colorama_init


def simulate_youth_intake():
    """模拟青训球员选拔"""
    colorama_init()

    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'YOUTH ACADEMY INTAKE SIMULATION':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")

    generator = YouthAcademyGenerator(seed=random.randint(1, 1000))

    # 模拟不同级别的青训营
    academies = [
        ("Manchester City Academy", 95, 9500),
        ("Southampton Academy", 75, 6500),
        ("League Two Academy", 45, 3500),
    ]

    for academy_name, level, reputation in academies:
        print(f"\n{Fore.YELLOW}{academy_name}{Style.RESET_ALL}")
        print(f"Academy Level: {level}/100 | Club Reputation: {reputation}")
        print("-" * 80)

        config = YouthIntakeConfig(
            academy_level=level,
            players_per_intake=4,
        )

        players = generator.generate_youth_intake(
            club_id=1,
            club_reputation=reputation,
            config=config,
            intake_date=date(2024, 7, 1),
        )

        print(f"{'Name':<25} {'Age':<5} {'Pos':<5} {'CA':<4} {'PA':<4} {'Gap':<5} {'Value':<12}")
        print("-" * 80)

        for player in players:
            gap = player.potential_ability - player.current_ability
            print(
                f"{player.full_name:<25} {player.age:<5} {player.position.value:<5} "
                f"{player.current_ability:<4} {player.potential_ability:<4} {gap:<5} "
                f"€{player.market_value:>10,}"
            )


def simulate_player_career():
    """模拟一个球员的完整职业生涯"""
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'PLAYER CAREER SIMULATION':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")

    engine = PlayerDevelopmentEngine(seed=42)
    tracker = DevelopmentTracker()

    current_year = 2024
    player = Player(
        id=1,
        first_name="Alex",
        last_name="Johnson",
        birth_date=date(current_year - 16, 3, 15),
        position=Position.ST,
        current_ability=35,
        potential_ability=88,
        nationality="England",
    )

    print(f"\n{Fore.GREEN}Player Profile:{Style.RESET_ALL}")
    print(f"Name: {player.full_name}")
    print(f"Position: {player.position.value}")
    print(f"Starting Age: {player.age}")
    print(f"Starting Ability: {player.current_ability}")
    print(f"Potential: {player.potential_ability}")

    print(f"\n{Fore.YELLOW}Career Progression:{Style.RESET_ALL}")
    print(
        f"{'Age':<5} {'Phase':<15} {'Minutes':<10} {'Old CA':<8} {'New CA':<8} {'Growth':<8} {'Notes':<20}"
    )
    print("-" * 100)

    # 模拟每个赛季 (16岁到38岁)
    start_age = 16
    for season in range(22):
        age = start_age + season
        phase = engine.get_development_phase(age)

        # 模拟出场时间（年轻时少，巅峰时多，老年时少）
        if age <= 19:
            minutes = random.randint(500, 1500)
        elif age <= 28:
            minutes = random.randint(2000, 3200)
        elif age <= 33:
            minutes = random.randint(1500, 2500)
        else:
            minutes = random.randint(200, 1000)

        old_ability = player.current_ability

        current_year = 2024 + season
        if player.birth_date is not None:
            player.birth_date = date(
                current_year - age, player.birth_date.month, player.birth_date.day
            )

        # 检查退役
        should_retire, reason = engine.check_retirement(player)
        if should_retire:
            print(
                f"{age:<5} {phase.name:<15} {'N/A':<10} {old_ability:<8} {'N/A':<8} {'N/A':<8} "
                f"{Fore.RED}RETIRED - {reason}{Style.RESET_ALL}"
            )
            break

        # 计算赛季发展
        result = engine.calculate_season_development(
            player=player,
            minutes_played=minutes,
            training_quality=75,
        )

        # 记录发展
        tracker.record_season(player, minutes, result)

        # 显示结果
        growth_str = f"{result['growth']:+d}"
        notes = ""

        if result["growth"] > 5:
            notes = f"{Fore.GREEN}Excellent season!{Style.RESET_ALL}"
        elif result["growth"] < -3:
            notes = f"{Fore.RED}Declining{Style.RESET_ALL}"
        elif age == 20:
            notes = "Breakthrough year"
        elif age == 28:
            notes = "Peak years"

        print(
            f"{age:<5} {phase.name:<15} {minutes:<10} {old_ability:<8} "
            f"{player.current_ability:<8} {growth_str:<8} {notes:<20}"
        )

    # 显示生涯总结
    summary = tracker.get_development_summary(player.id)
    if summary:
        print(f"\n{Fore.GREEN}Career Summary:{Style.RESET_ALL}")
        print(f"Total Growth: {summary['total_growth']} points")
        print(f"Seasons Played: {summary['seasons_tracked']}")
        print(f"Total Minutes: {summary['total_minutes']:,}")
        print(f"Final Ability: {player.current_ability}")


def simulate_injury_impact():
    """模拟伤病对球员的影响"""
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'INJURY IMPACT SIMULATION':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")

    print(
        f"\n{Fore.YELLOW}Testing 5 different scenarios with same injury severity:{Style.RESET_ALL}"
    )
    print(f"{'Scenario':<12} {'CA Before':<12} {'CA After':<12} {'Potential':<12} {'Effects':<30}")
    print("-" * 80)

    scenarios_with_damage = 0

    for i in range(5):
        engine = PlayerDevelopmentEngine(seed=None)

        # 创建一个22岁的球员
        player = Player(
            id=2,
            first_name="Michael",
            last_name="Brown",
            birth_date=date(2002, 6, 1),
            position=Position.CM,
            current_ability=70,
            potential_ability=85,
            pace=75,
            acceleration=72,
            stamina=78,
            strength=70,
        )

        old_ca = player.current_ability
        old_potential = player.potential_ability

        result = engine.apply_injury_recovery(
            player=player,
            injury_severity=4,  # Serious
            recovery_weeks=24,
        )

        if result["permanent_reduction"]:
            scenarios_with_damage += 1
            effects = f"{len(result['reduced_attributes'])} attrs reduced"
            if result["potential_capped"]:
                effects += ", potential capped"
            color = Fore.RED
        else:
            effects = "No permanent damage"
            color = Fore.GREEN

        print(
            f"{f'Scenario {i + 1}':<12} {old_ca:<12} {player.current_ability:<12} "
            f"{player.potential_ability:<12} {color}{effects:<30}{Style.RESET_ALL}"
        )

    print(
        f"\n{Fore.CYAN}Summary: {scenarios_with_damage}/5 scenarios had permanent damage{Style.RESET_ALL}"
    )
    print(f"{Fore.CYAN}Expected probability for severity 4: ~45-70%{Style.RESET_ALL}")


def simulate_age_decline():
    """模拟年龄相关的属性下滑"""
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'AGE-RELATED DECLINE SIMULATION':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")

    engine = PlayerDevelopmentEngine(seed=42)

    # 创建一个30岁的球员
    player = Player(
        id=3,
        first_name="David",
        last_name="Smith",
        birth_date=date(1994, 1, 1),
        position=Position.ST,
        current_ability=78,
        potential_ability=80,
        pace=85,
        acceleration=82,
        stamina=80,
        strength=75,
        shooting=80,
        passing=70,
    )

    print(f"\n{Fore.GREEN}Player at Age 30:{Style.RESET_ALL}")
    print(f"Overall: {player.current_ability}")
    print(f"Pace: {player.pace}")
    print(f"Acceleration: {player.acceleration}")
    print(f"Stamina: {player.stamina}")
    print(f"Strength: {player.strength}")
    print(f"Shooting: {player.shooting}")

    print(f"\n{Fore.YELLOW}Simulating 5 years of decline...{Style.RESET_ALL}")
    print(f"{'Age':<5} {'Overall':<10} {'Pace':<8} {'Acc':<8} {'Stam':<8} {'Str':<8} {'Shoot':<8}")
    print("-" * 70)

    for year in range(6):
        age = 30 + year

        current_year = 2024 + year
        if player.birth_date is not None:
            player.birth_date = date(current_year - age, 1, 1)

        # 模拟赛季
        result = engine.calculate_season_development(
            player=player,
            minutes_played=2000,
            training_quality=70,
        )

        decline_marker = ""
        if result.get("growth", 0) < -2:
            decline_marker = f"{Fore.RED}▼{Style.RESET_ALL}"
        elif result.get("growth", 0) < 0:
            decline_marker = f"{Fore.YELLOW}▼{Style.RESET_ALL}"

        print(
            f"{age:<5} {player.current_ability:<10} {player.pace:<8} "
            f"{player.acceleration:<8} {player.stamina:<8} {player.strength:<8} "
            f"{player.shooting:<8} {decline_marker}"
        )


def main():
    """主函数"""
    colorama_init()

    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'PLAYER DEVELOPMENT SYSTEM':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")

    # 运行所有模拟
    simulate_youth_intake()
    simulate_player_career()
    simulate_injury_impact()
    simulate_age_decline()

    print(f"\n{Fore.GREEN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'SIMULATION COMPLETE':^80}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'=' * 80}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
