#!/usr/bin/env python3
"""Import players from players_en.csv to database.

Usage:
    python scripts/import_players_en.py
"""

import asyncio
import sys
import re
from pathlib import Path
from datetime import datetime, date
from typing import Optional

import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.core.models import Player, Club, League, Position, Foot, WorkRate


def parse_percentage(value) -> float:
    """Parse percentage string to float."""
    if pd.isna(value):
        return 0.0
    value_str = str(value)
    match = re.search(r"([\d.]+)%", value_str)
    if match:
        return float(match.group(1))
    try:
        return float(value_str)
    except:
        return 0.0


def parse_money(value) -> int:
    """Parse money string to integer."""
    if pd.isna(value):
        return 0
    value_str = str(value).replace(",", "").replace("$", "").replace("€", "").replace("-", "")
    try:
        return int(float(value_str))
    except:
        return 0


def parse_int(value) -> int:
    """Parse integer from various formats."""
    if pd.isna(value):
        return 0
    value_str = str(value).replace(",", "").replace("-", "")
    try:
        return int(float(value_str))
    except:
        return 0


def split_name(full_name: str) -> tuple[str, str]:
    """Split full name into first and last name."""
    if not full_name or "," not in full_name:
        parts = full_name.split()
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])

    # Handle "Last, First" format
    parts = full_name.split(",")
    last_name = parts[0].strip()
    first_name = parts[1].strip() if len(parts) > 1 else ""
    return first_name, last_name


def map_position(pos_str: str) -> Position:
    """Map position string to Position enum."""
    if not pos_str:
        return Position.CM

    pos_str = str(pos_str).strip().upper()

    # Direct mapping for common abbreviations
    position_map = {
        "GK": Position.GK,
        "SW": Position.CB,  # Sweeper maps to CB
        "DL": Position.LB,
        "DC": Position.CB,
        "DR": Position.RB,
        "D L": Position.LB,
        "D C": Position.CB,
        "D R": Position.RB,
        "D RC": Position.CB,
        "D LC": Position.CB,
        "WBL": Position.LWB,
        "WBR": Position.RWB,
        "DM": Position.CDM,
        "ML": Position.LM,
        "MC": Position.CM,
        "MR": Position.RM,
        "M C": Position.CM,
        "M L": Position.LM,
        "M R": Position.RM,
        "AML": Position.LW,
        "AMC": Position.CAM,
        "AMR": Position.RW,
        "AM L": Position.LW,
        "AM R": Position.RW,
        "AM C": Position.CAM,
        "AM RL": Position.CAM,
        "AM RLC": Position.CAM,
        "AM RC": Position.CAM,
        "AM/F C": Position.CAM,
        "FS": Position.CF,
        "TS": Position.ST,
        "ST": Position.ST,
        "CF": Position.CF,
        "D/WB L": Position.LWB,
        "D/WB R": Position.RWB,
        "D/WB/M L": Position.LM,
        "D/WB/M R": Position.RM,
        "WB L": Position.LWB,
        "WB R": Position.RWB,
        "WB/M R": Position.RM,
    }

    # Try direct match first
    if pos_str in position_map:
        return position_map[pos_str]

    # Try to find partial match
    for key, value in position_map.items():
        if key in pos_str:
            return value

    return Position.CM


def parse_date(date_str: str) -> Optional[date]:
    """Parse date string to date object."""
    if not date_str or date_str == "-":
        return None

    try:
        # Format: DD.MM.YYYY
        return datetime.strptime(str(date_str), "%d.%m.%Y").date()
    except:
        try:
            # Format: YYYY-MM-DD
            return datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except:
            return None


def parse_fitness(value) -> int:
    """Parse fitness/jadedness value."""
    val = parse_int(value)
    # Jadedness is negative, convert to fitness (0-100)
    if val < 0:
        return max(0, 100 + val)
    return min(100, val)


async def import_players():
    """Import players from CSV to database."""
    csv_file = project_root / "data" / "players_en.csv"

    if not csv_file.exists():
        print(f"❌ File not found: {csv_file}")
        return False

    print("🚀 Initializing database...")
    await init_db()
    session_maker = get_session_maker()

    # Read CSV
    print("📊 Reading CSV file...")
    df = pd.read_csv(csv_file, encoding="latin-1", sep=";")
    print(f"   Found {len(df)} players")

    async with session_maker() as session:
        # Get existing clubs for mapping
        result = await session.execute(select(Club))
        existing_clubs = {c.name: c.id for c in result.scalars().all()}
        print(f"   Found {len(existing_clubs)} existing clubs")

        # Process players
        print("\n👤 Importing players...")
        imported = 0
        skipped = 0
        errors = 0

        batch_size = 100
        players_batch = []

        for idx, row in df.iterrows():
            try:
                # Skip if player already exists
                uid = parse_int(row.get("Unique ID"))
                result = await session.execute(select(Player).where(Player.id == uid))
                if result.scalar_one_or_none():
                    skipped += 1
                    continue

                # Parse name
                full_name = str(row.get("Name", ""))
                first_name, last_name = split_name(full_name)

                # Parse position
                position = map_position(row.get("Position", ""))

                # Parse dates
                birth_date = parse_date(row.get("Date Of Birth"))
                contract_end = parse_date(row.get("Contract End"))

                # Get club ID
                club_id = parse_int(row.get("Club ID"))
                if club_id == -1:
                    club_id = None

                # Parse fitness (from Jadedness column)
                fitness = parse_fitness(row.get("Jdns"))

                # Create player
                player = Player(
                    id=uid,
                    first_name=first_name,
                    last_name=last_name,
                    nationality=str(row.get("Nation", "Unknown")),
                    position=position,
                    birth_date=birth_date,
                    # Physical attributes
                    pace=0,  # Will be calculated from position ratings
                    acceleration=0,
                    stamina=parse_int(row.get("Fitness")),
                    strength=0,
                    # Technical attributes (default to current ability based)
                    current_ability=int(parse_percentage(row.get("Best Rating"))),
                    potential_ability=int(parse_percentage(row.get("Best Pot Rating"))),
                    # Contract info
                    club_id=club_id,
                    salary=parse_money(row.get("Wage")),
                    market_value=parse_money(row.get("Value")),
                    contract_until=contract_end,
                    release_clause=parse_money(row.get("Minimum Fee")),
                    # Status
                    fitness=fitness,
                    morale=parse_int(row.get("Happiness Level")),
                    form=int(parse_percentage(row.get("Con"))),
                )

                players_batch.append(player)

                # Commit batch
                if len(players_batch) >= batch_size:
                    for p in players_batch:
                        session.add(p)
                    await session.commit()
                    imported += len(players_batch)
                    players_batch = []

                    if imported % 1000 == 0:
                        print(f"   {imported} players imported...")

            except Exception as e:
                errors += 1
                if errors <= 5:  # Show first 5 errors
                    print(f"   ⚠️ Error on row {idx}: {e}")
                continue

        # Commit remaining players
        if players_batch:
            for p in players_batch:
                session.add(p)
            await session.commit()
            imported += len(players_batch)

        # Print summary
        print("\n" + "=" * 60)
        print("📈 IMPORT SUMMARY")
        print("=" * 60)
        print(f"   Total: {len(df)}")
        print(f"   Imported: {imported}")
        print(f"   Skipped (exists): {skipped}")
        print(f"   Errors: {errors}")

        # Show sample players
        result = await session.execute(select(Player).limit(5))
        sample_players = result.scalars().all()
        print("\n📝 Sample imported players:")
        for p in sample_players:
            print(f"   {p.full_name} ({p.position.value}) - CA: {p.current_ability}")

    await close_db()
    print("\n✅ Import complete!")
    return True


if __name__ == "__main__":
    asyncio.run(import_players())
