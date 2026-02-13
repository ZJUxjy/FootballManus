#!/usr/bin/env python3
"""初始化俱乐部数据

为现有俱乐部创建默认设施、员工和赞助商
Usage:
    python scripts/init_club_data.py
"""

import asyncio
import random
from datetime import date, timedelta

from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.core.models.club import Club
from fm_manager.core.models.facility import Facility, FacilityType, calculate_upgrade_cost, get_level_config
from fm_manager.core.models.staff import Staff, StaffRole
from fm_manager.core.models.sponsorship import Sponsor, SponsorLevel, SponsorType
from sqlalchemy import select


# 赞助商名称库
SPONSOR_NAMES = {
    SponsorLevel.GLOBAL: ["Nike", "Adidas", "Puma", "Fly Emirates", "Qatar Airways", "Etihad Airways"],
    SponsorLevel.PREMIUM: ["Heineken", "Pepsi", "Coca-Cola", "Budweiser", "Mastercard", "Visa"],
    SponsorLevel.MAJOR: ["Bet365", "Unilever", "Samsung", "LG", "Toyota", "Hyundai"],
    SponsorLevel.REGIONAL: ["Local Bank", "Regional Telecom", "City Hotel", "Regional Airline"],
    SponsorLevel.LOCAL: ["Local Restaurant", "Car Dealership", "Insurance Agent", "Real Estate"]
}

# 员工姓名库
FIRST_NAMES = ["John", "Michael", "David", "Robert", "James", "William", "Thomas", "Richard", "Daniel", "Paul",
               "Marco", "Luca", "Giuseppe", "Antonio", "Francesco", "Mario", "Giovanni", "Luigi",
               "Juan", "Pedro", "Luis", "Carlos", "Miguel", "Jose", "Antonio", "Francisco",
               "Hans", "Klaus", "Wolfgang", "Dieter", "Manfred", "Peter", "Michael", "Andreas"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson",
              "Rossi", "Ferrari", "Bianchi", "Romano", "Colombo", "Ricci", "Marino", "Greco",
              "Garcia", "Rodriguez", "Gonzalez", "Fernandez", "Lopez", "Martinez", "Sanchez",
              "Muller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner"]


async def create_default_facilities(session, club: Club):
    """为俱乐部创建默认设施"""
    
    # 根据俱乐部声誉决定初始设施等级
    reputation = club.reputation
    
    if reputation >= 8000:  # 顶级俱乐部
        initial_levels = {
            FacilityType.TRAINING_GROUND: 15,
            FacilityType.YOUTH_ACADEMY: 12,
            FacilityType.MEDICAL_CENTER: 14,
            FacilityType.DATA_ANALYTICS: 13,
            FacilityType.SCOUTING_NETWORK: 12,
            FacilityType.STADIUM: 18
        }
    elif reputation >= 5000:  # 中上游俱乐部
        initial_levels = {
            FacilityType.TRAINING_GROUND: 10,
            FacilityType.YOUTH_ACADEMY: 8,
            FacilityType.MEDICAL_CENTER: 9,
            FacilityType.DATA_ANALYTICS: 7,
            FacilityType.SCOUTING_NETWORK: 8,
            FacilityType.STADIUM: 12
        }
    elif reputation >= 2000:  # 中下游俱乐部
        initial_levels = {
            FacilityType.TRAINING_GROUND: 6,
            FacilityType.YOUTH_ACADEMY: 4,
            FacilityType.MEDICAL_CENTER: 5,
            FacilityType.DATA_ANALYTICS: 3,
            FacilityType.SCOUTING_NETWORK: 4,
            FacilityType.STADIUM: 8
        }
    else:  # 低级俱乐部
        initial_levels = {
            FacilityType.TRAINING_GROUND: 3,
            FacilityType.YOUTH_ACADEMY: 2,
            FacilityType.MEDICAL_CENTER: 2,
            FacilityType.DATA_ANALYTICS: 1,
            FacilityType.SCOUTING_NETWORK: 2,
            FacilityType.STADIUM: 4
        }
    
    facilities = []
    for facility_type, level in initial_levels.items():
        config = get_level_config(facility_type, level)
        
        facility = Facility(
            club_id=club.id,
            facility_type=facility_type,
            level=level,
            upgrade_cost=calculate_upgrade_cost(get_base_cost(facility_type), level),
            weekly_maintenance=config.weekly_maintenance if hasattr(config, 'weekly_maintenance') else calculate_maintenance_cost(facility_type, level)
        )
        facilities.append(facility)
    
    for facility in facilities:
        session.add(facility)
    
    return facilities


def get_base_cost(facility_type: FacilityType) -> int:
    """获取设施基础成本"""
    base_costs = {
        FacilityType.YOUTH_ACADEMY: 500000,
        FacilityType.TRAINING_GROUND: 400000,
        FacilityType.DATA_ANALYTICS: 300000,
        FacilityType.MEDICAL_CENTER: 200000,
        FacilityType.SCOUTING_NETWORK: 150000,
        FacilityType.STADIUM: 1000000
    }
    return base_costs.get(facility_type, 100000)


def calculate_maintenance_cost(facility_type: FacilityType, level: int) -> int:
    """计算维护成本"""
    base_maintenance = {
        FacilityType.YOUTH_ACADEMY: 5000,
        FacilityType.TRAINING_GROUND: 8000,
        FacilityType.DATA_ANALYTICS: 6000,
        FacilityType.MEDICAL_CENTER: 7000,
        FacilityType.SCOUTING_NETWORK: 4000,
        FacilityType.STADIUM: 15000
    }
    base = base_maintenance.get(facility_type, 5000)
    return int(base * (1 + level * 0.1))


async def create_default_staff(session, club: Club):
    """为俱乐部创建默认员工"""
    
    staff_members = []
    
    # 主教练 - 必须有
    head_coach = create_staff_member(club, StaffRole.HEAD_COACH, club.reputation)
    staff_members.append(head_coach)
    
    # 根据声誉决定额外员工
    reputation = club.reputation
    
    if reputation >= 3000:
        staff_members.append(create_staff_member(club, StaffRole.ASSISTANT_MANAGER, reputation * 0.8))
    
    if reputation >= 4000:
        staff_members.append(create_staff_member(club, StaffRole.GOALKEEPER_COACH, reputation * 0.7))
    
    if reputation >= 2000:
        staff_members.append(create_staff_member(club, StaffRole.FITNESS_COACH, reputation * 0.75))
    
    if reputation >= 5000:
        staff_members.append(create_staff_member(club, StaffRole.CHIEF_SCOUT, reputation * 0.8))
    
    if reputation >= 3500:
        staff_members.append(create_staff_member(club, StaffRole.HEAD_PHYSIO, reputation * 0.7))
    
    for staff in staff_members:
        session.add(staff)
    
    return staff_members


def create_staff_member(club: Club, role: StaffRole, ability_base: float) -> Staff:
    """创建单个员工"""
    
    # 根据基础能力生成具体能力值
    ability_variation = random.uniform(-5, 5)
    coaching_ability = min(100, max(30, int(ability_base / 100 * 70 + ability_variation)))
    
    # 根据角色调整能力
    if role == StaffRole.CHIEF_SCOUT:
        scouting_ability = coaching_ability
        medical_ability = random.randint(30, 50)
    elif role == StaffRole.HEAD_PHYSIO:
        scouting_ability = random.randint(30, 50)
        medical_ability = coaching_ability
    else:
        scouting_ability = random.randint(40, 60)
        medical_ability = random.randint(40, 60)
    
    # 计算薪资
    weekly_wage = calculate_staff_wage(role, coaching_ability)
    
    return Staff(
        club_id=club.id,
        first_name=random.choice(FIRST_NAMES),
        last_name=random.choice(LAST_NAMES),
        nationality="English",
        birth_date=date.today().replace(year=date.today().year - random.randint(35, 60)),
        role=role,
        ability=coaching_ability,
        salary=weekly_wage,
        contract_until=date.today() + timedelta(days=random.randint(365, 1095)),
        reputation=int(ability_base)
    )


def calculate_staff_wage(role: StaffRole, ability: int) -> int:
    """计算员工薪资"""
    base_wages = {
        StaffRole.HEAD_COACH: 5000,
        StaffRole.ASSISTANT_MANAGER: 3000,
        StaffRole.GOALKEEPER_COACH: 2500,
        StaffRole.FITNESS_COACH: 2000,
        StaffRole.CHIEF_SCOUT: 3500,
        StaffRole.HEAD_PHYSIO: 2200
    }
    
    base = base_wages.get(role, 2000)
    ability_multiplier = 1 + (ability - 50) / 100  # 50能力=1.0, 100能力=1.5
    
    return int(base * ability_multiplier)


async def create_sponsors(session, club: Club):
    """为俱乐部创建赞助商"""
    
    sponsors = []
    reputation = club.reputation
    
    # 确定赞助级别
    if reputation >= 10000:
        main_level = SponsorLevel.GLOBAL
        kit_level = SponsorLevel.PREMIUM
    elif reputation >= 7000:
        main_level = SponsorLevel.PREMIUM
        kit_level = SponsorLevel.MAJOR
    elif reputation >= 4000:
        main_level = SponsorLevel.MAJOR
        kit_level = SponsorLevel.MAJOR
    elif reputation >= 2000:
        main_level = SponsorLevel.REGIONAL
        kit_level = SponsorLevel.REGIONAL
    else:
        main_level = SponsorLevel.LOCAL
        kit_level = SponsorLevel.LOCAL
    
    # 主赞助商
    main_sponsor = create_sponsor(club, main_level, SponsorType.MAIN_SPONSOR)
    sponsors.append(main_sponsor)
    
    # 球衣赞助商
    kit_sponsor = create_sponsor(club, kit_level, SponsorType.KIT_SPONSOR)
    sponsors.append(kit_sponsor)
    
    # 顶级俱乐部可能有额外赞助商
    if reputation >= 8000:
        sponsors.append(create_sponsor(club, SponsorLevel.MAJOR, SponsorType.SLEEVE_SPONSOR))
    
    for sponsor in sponsors:
        session.add(sponsor)
    
    return sponsors


def create_sponsor(club: Club, level: SponsorLevel, sponsor_type: SponsorType) -> Sponsor:
    """创建单个赞助商"""

    annual_payment = calculate_sponsorship_amount(club.reputation, level, sponsor_type)
    base_name = random.choice(SPONSOR_NAMES[level])
    type_suffix = sponsor_type.value.replace("_", " ").title()
    unique_name = f"{base_name} - {type_suffix} ({club.short_name})"

    return Sponsor(
        club_id=club.id,
        name=unique_name,
        industry="Sports",
        level=level,
        sponsor_type=sponsor_type,
        base_annual_payment=annual_payment,
        contract_start=date.today(),
        contract_end=date.today() + timedelta(days=random.randint(730, 1460))
    )


def calculate_sponsorship_amount(reputation: int, level: SponsorLevel, sponsor_type: SponsorType) -> int:
    """计算赞助金额"""
    
    base_amounts = {
        SponsorLevel.GLOBAL: (100_000_000, 200_000_000),
        SponsorLevel.PREMIUM: (50_000_000, 100_000_000),
        SponsorLevel.MAJOR: (20_000_000, 50_000_000),
        SponsorLevel.REGIONAL: (5_000_000, 20_000_000),
        SponsorLevel.LOCAL: (1_000_000, 5_000_000)
    }
    
    min_amount, max_amount = base_amounts.get(level, (1_000_000, 5_000_000))
    
    # 根据类型调整
    type_multipliers = {
        SponsorType.MAIN_SPONSOR: 1.0,
        SponsorType.KIT_SPONSOR: 0.8,
        SponsorType.STADIUM_NAMING: 1.2,
        SponsorType.SLEEVE_SPONSOR: 0.3,
        SponsorType.TRAINING_KIT: 0.2,
        SponsorType.OFFICIAL_PARTNER: 0.4
    }
    
    base = random.randint(min_amount, max_amount)
    multiplier = type_multipliers.get(sponsor_type, 1.0)
    
    return int(base * multiplier)


async def main():
    print("🚀 初始化俱乐部数据")
    print("=" * 70)
    
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # 获取所有俱乐部
        result = await session.execute(select(Club))
        clubs = result.scalars().all()
        
        print(f"找到 {len(clubs)} 个俱乐部")
        
        total_facilities = 0
        total_staff = 0
        total_sponsors = 0
        
        for i, club in enumerate(clubs, 1):
            print(f"\n[{i}/{len(clubs)}] 处理俱乐部: {club.name} (声誉: {club.reputation})")
            
            # 创建设施
            facilities = await create_default_facilities(session, club)
            total_facilities += len(facilities)
            print(f"  ✓ 创建 {len(facilities)} 个设施")
            
            # 创建员工
            staff = await create_default_staff(session, club)
            total_staff += len(staff)
            print(f"  ✓ 创建 {len(staff)} 名员工")
            
            # 创建赞助商
            sponsors = await create_sponsors(session, club)
            total_sponsors += len(sponsors)
            print(f"  ✓ 创建 {len(sponsors)} 个赞助商")
        
        await session.commit()
        
        print("\n" + "=" * 70)
        print("✅ 数据初始化完成!")
        print(f"   总设施: {total_facilities}")
        print(f"   总员工: {total_staff}")
        print(f"   总赞助商: {total_sponsors}")
        print("=" * 70)
    
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
