#!/usr/bin/env python3
"""快速添加测试俱乐部"""

import asyncio
import sys
sys.path.insert(0, '.')

from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.core.models.club import Club
from fm_manager.core.models.league import League
from sqlalchemy import select

async def add_test_clubs():
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # 先检查是否有联赛
        result = await session.execute(select(League))
        leagues = result.scalars().all()
        
        if not leagues:
            print("⚠️  没有联赛数据，先创建测试联赛...")
            epl = League(
                name="Premier League",
                short_name="EPL",
                country="England",
                tier=1
            )
            session.add(epl)
            await session.flush()
            print(f"✅ 创建联赛: {epl.name} (ID: {epl.id})")
        else:
            epl = leagues[0]
            print(f"✅ 使用现有联赛: {epl.name}")
        
        # 创建测试俱乐部
        test_clubs = [
            {"name": "Manchester United", "short_name": "MUN", "reputation": 9200},
            {"name": "Liverpool", "short_name": "LIV", "reputation": 9000},
            {"name": "Manchester City", "short_name": "MCI", "reputation": 9100},
            {"name": "Chelsea", "short_name": "CHE", "reputation": 8800},
            {"name": "Arsenal", "short_name": "ARS", "reputation": 8700},
        ]
        
        added_count = 0
        for club_data in test_clubs:
            # 检查是否已存在
            result = await session.execute(
                select(Club).where(Club.name == club_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                club = Club(
                    name=club_data["name"],
                    short_name=club_data["short_name"],
                    reputation=club_data["reputation"],
                    league_id=epl.id,
                    balance=100_000_000,
                    transfer_budget=50_000_000,
                    wage_budget=2_000_000
                )
                session.add(club)
                added_count += 1
                print(f"  ➕ 添加俱乐部: {club_data['name']}")
        
        await session.commit()
        print(f"\n✅ 添加了 {added_count} 个测试俱乐部")
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(add_test_clubs())
