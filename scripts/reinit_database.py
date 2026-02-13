#!/usr/bin/env python3
"""重新初始化数据库 - 创建所有新表

Usage:
    python scripts/reinit_database.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.core import init_db, close_db


async def main():
    print("🔄 重新初始化数据库...")
    print("=" * 60)
    
    try:
        await init_db()
        print("✅ 数据库表创建成功!")
        print("\n已创建的表:")
        print("  - clubs (俱乐部)")
        print("  - players (球员)")
        print("  - matches (比赛)")
        print("  - facilities (设施) ✨ 新")
        print("  - staff (员工) ✨ 新")
        print("  - sponsors (赞助商) ✨ 新")
        print("=" * 60)
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
