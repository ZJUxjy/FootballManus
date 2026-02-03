"""Import Football Manager 2024 data into the database.

Usage:
    python scripts/import_fm_data.py <csv_file> [--limit N] [--league LEAGUE]

Example:
    # Import all players from FM24 CSV
    python scripts/import_fm_data.py fm_players.csv

    # Import only top 1000 players by CA
    python scripts/import_fm_data.py fm_players.csv --limit 1000

    # Import only Premier League players
    python scripts/import_fm_data.py fm_players.csv --league "Premier League"
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from fm_manager.data.fm_importer import FM24Importer, download_fm24_dataset_instructions
from fm_manager.core.database import SessionLocal
from fm_manager.core.models import Player, Club, League


def import_players(csv_file: str, limit: int | None = None, league_filter: str | None = None):
    """Import players from FM24 CSV file."""
    print(f"📂 读取 FM24 数据: {csv_file}")

    # Parse CSV
    importer = FM24Importer(csv_file)
    players = importer.parse_csv()

    print(f"✓ 解析了 {len(players)} 名球员")

    # Apply filters
    if limit:
        players = sorted(players, key=lambda p: p.current_ability, reverse=True)[:limit]
        print(f"✓ 筛选后保留 {len(players)} 名球员")

    if league_filter:
        # Filter by club league (needs additional logic)
        print(f"⚠️  联赛筛选需要额外的俱乐部数据")

    # Get unique clubs
    unique_clubs = importer.get_unique_clubs()
    print(f"✓ 发现 {len(unique_clubs)} 个俱乐部")

    # Create database session
    db = SessionLocal()

    try:
        # Create clubs first
        club_map = {}
        for club_name in unique_clubs:
            # Check if club exists
            club = db.query(Club).filter(Club.name == club_name).first()
            if not club:
                # Create new club
                club = Club(
                    name=club_name,
                    league_id=1,  # Default to first league (will update later)
                    reputation=50,
                    balance=50_000_000,  # Default balance
                )
                db.add(club)
                db.commit()
                db.refresh(club)
                print(f"  ✓ 创建俱乐部: {club_name}")

            club_map[club_name] = club

        # Import players
        imported_count = 0
        for fm_player in players:
            club_id = club_map.get(fm_player.club)
            if not club_id:
                print(f"  ⚠️  跳过 {fm_player.name} - 俱乐部 '{fm_player.club}' 不存在")
                continue

            # Check if player already exists (by name)
            existing = db.query(Player).filter(
                Player.first_name == fm_player.name.split()[0],
                Player.last_name == " ".join(fm_player.name.split()[1:])
            ).first()

            if existing:
                # Update existing player
                db_player = importer.to_db_player(fm_player, club_id)
                existing.current_ability = db_player.current_ability
                existing.potential_ability = db_player.potential_ability
                existing.market_value = db_player.market_value
                existing.salary = db_player.salary
                db.commit()
                imported_count += 1
            else:
                # Create new player
                db_player = importer.to_db_player(fm_player, club_id)
                db.add(db_player)
                imported_count += 1

            if imported_count % 100 == 0:
                db.commit()
                print(f"  已导入 {imported_count} 名球员...")

        db.commit()
        print(f"\n✅ 成功导入 {imported_count} 名球员!")

        # Show statistics
        print("\n📊 数据统计:")
        total_players = db.query(Player).count()
        print(f"  数据库中总球员数: {total_players}")

        # Top 5 players by CA
        top_players = db.query(Player).order_by(Player.current_ability.desc()).limit(5).all()
        print(f"\n🏆 能力最高的 5 名球员:")
        for p in top_players:
            print(f"  {p.full_name} (CA: {p.current_ability}, PA: {p.potential_ability})")

    except Exception as e:
        print(f"❌ 导入失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="导入 Football Manager 2024 数据")
    parser.add_argument("csv_file", help="FM24 CSV 文件路径")
    parser.add_argument("--limit", type=int, help="限制导入的球员数量")
    parser.add_argument("--league", help="只导入特定联赛的球员")
    parser.add_argument("--info", action="store_true", help="显示导入指南")

    args = parser.parse_args()

    if args.info:
        download_fm24_dataset_instructions()
        return

    if not Path(args.csv_file).exists():
        print(f"❌ 文件不存在: {args.csv_file}")
        return

    import_players(args.csv_file, args.limit, args.league)


if __name__ == "__main__":
    main()
