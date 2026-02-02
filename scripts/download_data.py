#!/usr/bin/env python3
"""
Data download and import script for FM Manager.

This script helps download and import football data from various sources:
- FIFA datasets from Kaggle
- Football Manager exports
- Transfermarkt (via scraping)
- API-Football

Usage:
    python scripts/download_data.py --source kaggle --dataset fifa-24
    python scripts/download_data.py --source fm --file fm_export.csv
    python scripts/download_data.py --source transfermarkt --league premier-league
"""

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.data.fifa_importer import FIFAImporter, download_fifa_dataset_from_kaggle
from fm_manager.data.importer import DataImporter

DATA_DIR = project_root / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def check_kaggle_installed() -> bool:
    """Check if kaggle CLI is installed."""
    try:
        subprocess.run(["kaggle", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def download_kaggle_dataset(dataset: str, output_dir: Path) -> bool:
    """Download a dataset from Kaggle.
    
    Args:
        dataset: Dataset name, e.g., "stefanoleone992/fifa-22-complete-player-dataset"
        output_dir: Where to save the downloaded files
    """
    if not check_kaggle_installed():
        print("❌ Kaggle CLI not installed. Install with: pip install kaggle")
        print("   Also need to set up API credentials: https://www.kaggle.com/docs/api")
        return False
    
    try:
        print(f"📥 Downloading {dataset} from Kaggle...")
        subprocess.run(
            ["kaggle", "datasets", "download", "-d", dataset, "-p", str(output_dir)],
            check=True,
        )
        print("✅ Download complete")
        
        # Unzip
        zip_file = output_dir / f"{dataset.split('/')[-1]}.zip"
        if zip_file.exists():
            import zipfile
            with zipfile.ZipFile(zip_file, 'r') as z:
                z.extractall(output_dir)
            zip_file.unlink()
            print("✅ Extracted files")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Download failed: {e}")
        return False


def download_fifa_22():
    """Download FIFA 22 dataset from Kaggle."""
    dataset = "stefanoleone992/fifa-22-complete-player-dataset"
    output = DATA_DIR / "fifa-22"
    output.mkdir(exist_ok=True)
    
    if download_kaggle_dataset(dataset, output):
        print(f"\n✅ FIFA 22 data downloaded to {output}")
        print("   Look for players_22.csv or similar file")
        return True
    return False


def download_fifa_23():
    """Download FIFA 23 dataset from Kaggle."""
    dataset = "bryanb/fifa-player-stats-database"
    output = DATA_DIR / "fifa-23"
    output.mkdir(exist_ok=True)
    
    if download_kaggle_dataset(dataset, output):
        print(f"\n✅ FIFA 23 data downloaded to {output}")
        return True
    return False


def download_fifa_24():
    """Download FIFA 24 (EAFC 24) dataset from Kaggle."""
    dataset = "sagy6t9/fifa-24-player-stats"
    output = DATA_DIR / "fifa-24"
    output.mkdir(exist_ok=True)
    
    if download_kaggle_dataset(dataset, output):
        print(f"\n✅ FIFA 24 data downloaded to {output}")
        return True
    return False


def download_european_soccer_database():
    """Download European Soccer Database from Kaggle."""
    dataset = "hugomathien/soccer"
    output = DATA_DIR / "european-soccer"
    output.mkdir(exist_ok=True)
    
    if download_kaggle_dataset(dataset, output):
        print(f"\n✅ European Soccer Database downloaded to {output}")
        return True
    return False


async def import_fifa_data(csv_file: Path, limit: int | None = None):
    """Import FIFA data from CSV file to database."""
    print(f"📊 Importing FIFA data from {csv_file}...")
    
    if not csv_file.exists():
        print(f"❌ File not found: {csv_file}")
        return False
    
    importer = FIFAImporter(csv_file)
    players = importer.parse_csv()
    
    if limit:
        players = players[:limit]
    
    print(f"   Parsed {len(players)} players")
    print(f"   {len(importer.get_unique_clubs())} unique clubs")
    
    # Initialize database
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        db_importer = DataImporter(session)
        
        # Get unique clubs and create them
        clubs = importer.get_unique_clubs()
        print(f"\n🏟️ Creating {len(clubs)} clubs...")
        
        club_map = {}  # name -> id
        for i, club_name in enumerate(clubs):
            # Check if club already exists
            from sqlalchemy import select
            from fm_manager.core.models import Club as ClubModel
            
            result = await session.execute(
                select(ClubModel).where(ClubModel.name == club_name)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                club_map[club_name] = existing.id
            else:
                # Create new club
                club_data = {
                    "name": club_name,
                    "short_name": club_name[:3].upper(),
                    "reputation": 1000,
                    "balance": 10_000_000,
                    "transfer_budget": 5_000_000,
                    "wage_budget": 500_000,
                }
                club = await db_importer.import_clubs([club_data])
                if club:
                    club_map[club_name] = club[0].id
            
            if (i + 1) % 50 == 0:
                print(f"   {i + 1}/{len(clubs)} clubs...")
        
        await session.commit()
        
        # Create players
        print(f"\n👤 Creating {len(players)} players...")
        
        db_players = []
        for i, fifa_player in enumerate(players):
            club_id = club_map.get(fifa_player.club)
            db_player = importer.to_db_player(fifa_player, club_id)
            session.add(db_player)
            
            if (i + 1) % 100 == 0:
                print(f"   {i + 1}/{len(players)} players...")
                await session.commit()
        
        await session.commit()
        print(f"✅ Imported {len(players)} players")
    
    await close_db()
    return True


def list_data_sources():
    """List available data sources."""
    sources = {
        "kaggle-fifa-22": {
            "name": "FIFA 22 Complete Player Dataset",
            "size": "~18,000 players",
            "source": "Kaggle",
            "attributes": "90+ attributes per player",
            "command": "python scripts/download_data.py --source kaggle --dataset fifa-22",
        },
        "kaggle-fifa-23": {
            "name": "FIFA 23 Player Stats",
            "size": "~18,000 players",
            "source": "Kaggle",
            "attributes": "Standard FIFA attributes",
            "command": "python scripts/download_data.py --source kaggle --dataset fifa-23",
        },
        "kaggle-fifa-24": {
            "name": "FIFA 24 (EAFC 24) Player Stats",
            "size": "~18,000 players",
            "source": "Kaggle",
            "attributes": "Latest player data",
            "command": "python scripts/download_data.py --source kaggle --dataset fifa-24",
        },
        "kaggle-soccer": {
            "name": "European Soccer Database",
            "size": "25,000+ matches, 10,000+ players",
            "source": "Kaggle",
            "attributes": "Match data + player attributes",
            "command": "python scripts/download_data.py --source kaggle --dataset soccer",
        },
        "fm-export": {
            "name": "Football Manager Export",
            "size": "500,000+ players",
            "source": "FM Editor / Community",
            "attributes": "Most comprehensive",
            "note": "Requires manual export from FM or download from community sites",
        },
        "transfermarkt": {
            "name": "Transfermarkt Scraper",
            "size": "1,000,000+ players",
            "source": "Web Scraping",
            "attributes": "Market values, contracts, stats",
            "note": "Requires implementation of specific league scraping",
        },
    }
    
    print("\n📚 Available Data Sources:\n")
    for key, info in sources.items():
        print(f"  {key}:")
        print(f"    Name: {info['name']}")
        print(f"    Size: {info['size']}")
        print(f"    Source: {info['source']}")
        print(f"    Attributes: {info['attributes']}")
        if 'command' in info:
            print(f"    Command: {info['command']}")
        if 'note' in info:
            print(f"    Note: {info['note']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Download and import football data for FM Manager"
    )
    parser.add_argument(
        "--source",
        choices=["kaggle", "fm", "transfermarkt", "list"],
        help="Data source to use",
    )
    parser.add_argument(
        "--dataset",
        choices=["fifa-22", "fifa-23", "fifa-24", "soccer"],
        help="Specific dataset to download (for Kaggle)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Path to data file (for FM export or CSV import)",
    )
    parser.add_argument(
        "--import",
        dest="import_data",
        action="store_true",
        help="Import downloaded data to database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of players to import (for testing)",
    )
    
    args = parser.parse_args()
    
    if not args.source or args.source == "list":
        list_data_sources()
        return
    
    if args.source == "kaggle":
        if not args.dataset:
            print("❌ Please specify --dataset (fifa-22, fifa-23, fifa-24, soccer)")
            return
        
        success = False
        if args.dataset == "fifa-22":
            success = download_fifa_22()
        elif args.dataset == "fifa-23":
            success = download_fifa_23()
        elif args.dataset == "fifa-24":
            success = download_fifa_24()
        elif args.dataset == "soccer":
            success = download_european_soccer_database()
        
        if success and args.import_data:
            # Find the CSV file
            dataset_dir = DATA_DIR / args.dataset
            csv_files = list(dataset_dir.glob("*.csv"))
            
            if csv_files:
                print(f"\n📂 Found {len(csv_files)} CSV files")
                for csv_file in csv_files:
                    response = input(f"Import {csv_file.name}? [y/N] ")
                    if response.lower() == "y":
                        asyncio.run(import_fifa_data(csv_file, args.limit))
            else:
                print("❌ No CSV files found to import")
    
    elif args.source == "fm":
        if args.file:
            print(f"📂 Using FM export file: {args.file}")
            # TODO: Implement FM import
        else:
            print("ℹ️ To import Football Manager data:")
            print("   1. Open Football Manager")
            print("   2. Use the Editor to export data to CSV")
            print("   3. Run: python scripts/download_data.py --source fm --file <path>")
    
    elif args.source == "transfermarkt":
        print("ℹ️ Transfermarkt scraping:")
        print("   This requires implementing specific league scraping.")
        print("   See: fm_manager/data/transfermarkt_scraper.py")


if __name__ == "__main__":
    main()
