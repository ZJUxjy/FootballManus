#!/usr/bin/env python3
"""
Reset database and import real data
"""

import asyncio
import sys
sys.path.insert(0, '.')

from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.core.database import engine
from sqlalchemy import text

async def reset_database():
    print("🗑️  清理现有数据...")
    
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM players"))
        await conn.execute(text("DELETE FROM clubs"))
        await conn.execute(text("DELETE FROM leagues"))
        await conn.execute(text("DELETE FROM transfers"))
        await conn.execute(text("DELETE FROM matches"))
        await conn.execute(text("DELETE FROM facilities"))
        await conn.execute(text("DELETE FROM staff"))
        await conn.execute(text("DELETE FROM sponsors"))
    
    print("✅ 数据库已清理")

if __name__ == "__main__":
    asyncio.run(reset_database())
