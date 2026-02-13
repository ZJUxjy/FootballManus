#!/usr/bin/env python3
"""
添加测试球员
"""

import asyncio
import sys
sys.path.insert(0, '.')

from datetime import date, timedelta
from fm_manager.core import init_db, get_session_maker
from fm_manager.core.models.player import Player, Position, Foot
from fm_manager.core.models.club import Club
from sqlalchemy import select
import random

FIRST_NAMES = ["Marcus", "Bruno", "Mohamed", "Kevin", "Cristiano", "Lionel", "Robert", "Sadio", "Virgil", "Alisson",
               "Trent", "Andy", "Jordan", "Fabinho", "Thiago", "Diogo", "Luis", "Trent", "Joel", "Ibrahima"]

LAST_NAMES = ["Rashford", "Fernandes", "Salah", "De Bruyne", "Ronaldo", "Messi", "Lewandowski", "Mane", "van Dijk", "Becker",
              "Alexander-Arnold", "Robertson", "Henderson", "Silva", "Alcantara", "Jota", "Diaz", "Alexander-Arnold", "Matip", "Konate"]


def calculate_birth_date(age: int) -> date:
    today = date.today()
    birth_year = today.year - age
    try:
        return date(birth_year, today.month, today.day)
    except ValueError:
        return date(birth_year, today.month, 28)

async def add_test_players():
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        result = await session.execute(select(Club))
        clubs = result.scalars().all()
        
        if not clubs:
            print("❌ 没有俱乐部，请先创建俱乐部")
            return
        
        positions = [Position.GK, Position.CB, Position.LB, Position.RB, Position.CDM, 
                     Position.CM, Position.LM, Position.RM, Position.CAM, Position.LW, 
                     Position.RW, Position.ST]
        
        total_added = 0
        
        for club in clubs:
            for i in range(25):
                position = random.choice(positions)
                ca = random.randint(60, 90)
                pa = min(100, ca + random.randint(0, 20))
                age = random.randint(18, 35)
                
                birth_date = calculate_birth_date(age)

                player = Player(
                    first_name=random.choice(FIRST_NAMES),
                    last_name=random.choice(LAST_NAMES),
                    nationality="England",
                    birth_date=birth_date,
                    position=position,
                    club_id=club.id,
                    current_ability=ca,
                    potential_ability=pa,
                    preferred_foot=random.choice([Foot.LEFT, Foot.RIGHT]),
                    pace=random.randint(40, 90),
                    acceleration=random.randint(40, 90),
                    stamina=random.randint(40, 90),
                    strength=random.randint(40, 90),
                    shooting=random.randint(40, 90),
                    passing=random.randint(40, 90),
                    dribbling=random.randint(40, 90),
                    crossing=random.randint(40, 90),
                    first_touch=random.randint(40, 90),
                    tackling=random.randint(40, 90),
                    marking=random.randint(40, 90),
                    positioning=random.randint(40, 90),
                    vision=random.randint(40, 90),
                    decisions=random.randint(40, 90),
                    reflexes=random.randint(40, 90) if position == Position.GK else 50,
                    handling=random.randint(40, 90) if position == Position.GK else 50,
                    kicking=random.randint(40, 90) if position == Position.GK else 50,
                    one_on_one=random.randint(40, 90) if position == Position.GK else 50
                )
                session.add(player)
                total_added += 1
            
            print(f"✅ 为 {club.name} 添加 25 名球员")
        
        await session.commit()
        print(f"\n🎉 总共添加了 {total_added} 名测试球员")
    
    await close_db()

if __name__ == "__main__":
    from fm_manager.core import close_db
    asyncio.run(add_test_players())
