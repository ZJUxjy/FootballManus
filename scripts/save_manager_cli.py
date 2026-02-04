#!/usr/bin/env python3
"""Save/Load system CLI commands for FM Manager.

Commands:
    save list              - List all save files
    save info <name>       - Show detailed save info
    save create <name>     - Create new save
    save load <name>       - Load save file
    save delete <name>     - Delete save file
    save rename <old> <new> - Rename save file
    save duplicate <src> <new> - Duplicate save file
    save auto              - Toggle auto-save
    save backup <name>     - Create backup of save
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.core.save_load_enhanced import (
    EnhancedSaveLoadManager,
    get_save_manager,
    SaveMetadata,
)
from fm_manager.core.database import get_db_session
from colorama import Fore, Style, init as colorama_init


def format_file_size(size_bytes: int) -> str:
    """Format file size for display."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_duration(minutes: int) -> str:
    """Format play time duration."""
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def cmd_list(args):
    """List all save files."""
    manager = get_save_manager()
    saves = manager.get_save_files()

    if not saves:
        print(f"{Fore.YELLOW}No save files found.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.CYAN}{'Save Files':=^80}{Style.RESET_ALL}\n")

    # Header
    print(f"{'Name':<25} {'Date':<20} {'Season':<8} {'Club':<20} {'Size':<10}")
    print("-" * 80)

    for metadata, path in saves:
        is_auto = metadata.save_name.startswith(manager.AUTO_SAVE_PREFIX)
        name_display = metadata.save_name[:24]

        if is_auto:
            name_display = f"{Fore.YELLOW}[AUTO]{Style.RESET_ALL} {name_display[6:18]}"

        date_str = metadata.save_date.strftime("%Y-%m-%d %H:%M")
        season_str = f"S{metadata.current_season}W{metadata.current_week}"
        club_str = metadata.player_club_name or "No Club"
        club_str = club_str[:18]

        # Get file size
        size_str = format_file_size(path.stat().st_size)

        print(f"{name_display:<25} {date_str:<20} {season_str:<8} {club_str:<20} {size_str:<10}")

    print(f"\n{Fore.CYAN}Total: {len(saves)} save files{Style.RESET_ALL}")


def cmd_info(args):
    """Show detailed save info."""
    manager = get_save_manager()

    try:
        info = manager.get_save_info(args.name)
    except FileNotFoundError:
        print(f"{Fore.RED}Error: Save file '{args.name}' not found{Style.RESET_ALL}")
        return

    metadata = info.get("metadata", {})

    print(f"\n{Fore.CYAN}{'Save Information':=^80}{Style.RESET_ALL}\n")

    print(f"{Fore.GREEN}Basic Info:{Style.RESET_ALL}")
    print(f"  Name: {info['name']}")
    print(f"  Path: {info['path']}")
    print(f"  Size: {info['size_mb']} MB ({info['size_bytes']:,} bytes)")
    print(f"  Created: {info['created'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Modified: {info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")

    if metadata:
        print(f"\n{Fore.GREEN}Game State:{Style.RESET_ALL}")
        print(f"  Version: {metadata.get('version', 'Unknown')}")
        print(f"  Season: {metadata.get('current_season', 'N/A')}")
        print(f"  Week: {metadata.get('current_week', 'N/A')}")
        print(f"  In-Game Date: {metadata.get('in_game_date', 'N/A')}")
        print(f"  Play Time: {format_duration(metadata.get('play_time_minutes', 0))}")

        print(f"\n{Fore.GREEN}Player Info:{Style.RESET_ALL}")
        print(f"  Club: {metadata.get('player_club_name', 'No Club')}")
        print(f"  Club ID: {metadata.get('player_club_id', 'N/A')}")
        print(f"  League Position: {metadata.get('league_position', 'N/A')}")

        print(f"\n{Fore.GREEN}Statistics:{Style.RESET_ALL}")
        print(f"  Matches Played: {metadata.get('total_matches_played', 0)}")
        print(f"  Goals Scored: {metadata.get('total_goals_scored', 0)}")


def cmd_create(args):
    """Create new save."""
    manager = get_save_manager()

    # Get database session
    session = get_db_session()

    # For demo purposes, use default values
    # In real game, these would come from game state
    try:
        save_path = manager.save_game(
            session=session,
            save_name=args.name,
            current_season=args.season or 1,
            current_week=args.week or 1,
            player_club_id=args.club_id,
            in_game_date=datetime.now().date(),
        )

        print(f"{Fore.GREEN}✓ Save created successfully:{Style.RESET_ALL}")
        print(f"  Name: {args.name}")
        print(f"  Path: {save_path}")

    except Exception as e:
        print(f"{Fore.RED}Error creating save: {e}{Style.RESET_ALL}")


def cmd_load(args):
    """Load save file."""
    manager = get_save_manager()

    try:
        metadata, game_state = manager.load_game(args.name)

        print(f"{Fore.GREEN}✓ Save loaded successfully:{Style.RESET_ALL}")
        print(f"  Name: {metadata.save_name}")
        print(f"  Season: {metadata.current_season}, Week: {metadata.current_week}")
        print(f"  Club: {metadata.player_club_name or 'No Club'}")
        print(f"  In-Game Date: {metadata.in_game_date}")

        if not args.dry_run:
            # Restore to database
            session = get_db_session()
            manager.restore_game_state(session, game_state)
            print(f"{Fore.GREEN}✓ Game state restored to database{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}(Dry run - not restored){Style.RESET_ALL}")

    except FileNotFoundError:
        print(f"{Fore.RED}Error: Save file '{args.name}' not found{Style.RESET_ALL}")
    except ValueError as e:
        print(f"{Fore.RED}Error: Save file corrupted - {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error loading save: {e}{Style.RESET_ALL}")


def cmd_delete(args):
    """Delete save file."""
    manager = get_save_manager()

    if not args.force:
        confirm = input(f"Delete save '{args.name}'? (y/N): ")
        if confirm.lower() != "y":
            print(f"{Fore.YELLOW}Cancelled{Style.RESET_ALL}")
            return

    if manager.delete_save(args.name):
        print(f"{Fore.GREEN}✓ Save '{args.name}' deleted{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Error: Save file '{args.name}' not found{Style.RESET_ALL}")


def cmd_rename(args):
    """Rename save file."""
    manager = get_save_manager()

    try:
        new_path = manager.rename_save(args.old_name, args.new_name)
        print(f"{Fore.GREEN}✓ Save renamed:{Style.RESET_ALL}")
        print(f"  {args.old_name} -> {args.new_name}")
        print(f"  Path: {new_path}")
    except FileNotFoundError:
        print(f"{Fore.RED}Error: Save file '{args.old_name}' not found{Style.RESET_ALL}")
    except FileExistsError:
        print(f"{Fore.RED}Error: Save file '{args.new_name}' already exists{Style.RESET_ALL}")


def cmd_duplicate(args):
    """Duplicate save file."""
    manager = get_save_manager()

    try:
        new_path = manager.duplicate_save(args.source, args.new_name)
        print(f"{Fore.GREEN}✓ Save duplicated:{Style.RESET_ALL}")
        print(f"  Source: {args.source}")
        print(f"  New: {args.new_name}")
        print(f"  Path: {new_path}")
    except FileNotFoundError:
        print(f"{Fore.RED}Error: Save file '{args.source}' not found{Style.RESET_ALL}")
    except FileExistsError:
        print(f"{Fore.RED}Error: Save file '{args.new_name}' already exists{Style.RESET_ALL}")


def cmd_auto(args):
    """Toggle auto-save."""
    manager = get_save_manager()

    if args.status:
        status = "enabled" if manager.auto_save_enabled else "disabled"
        interval = manager.auto_save_interval_minutes
        print(
            f"Auto-save: {Fore.GREEN if manager.auto_save_enabled else Fore.RED}{status}{Style.RESET_ALL}"
        )
        print(f"Interval: {interval} minutes")
        return

    if args.enable:
        manager.auto_save_enabled = True
        print(f"{Fore.GREEN}✓ Auto-save enabled{Style.RESET_ALL}")
    elif args.disable:
        manager.auto_save_enabled = False
        print(f"{Fore.YELLOW}✓ Auto-save disabled{Style.RESET_ALL}")

    if args.interval:
        manager.auto_save_interval_minutes = args.interval
        print(f"{Fore.GREEN}✓ Auto-save interval set to {args.interval} minutes{Style.RESET_ALL}")


def cmd_backup(args):
    """Create backup of save."""
    manager = get_save_manager()

    backup_name = f"{args.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        new_path = manager.duplicate_save(args.name, backup_name)
        print(f"{Fore.GREEN}✓ Backup created:{Style.RESET_ALL}")
        print(f"  Original: {args.name}")
        print(f"  Backup: {backup_name}")
        print(f"  Path: {new_path}")
    except FileNotFoundError:
        print(f"{Fore.RED}Error: Save file '{args.name}' not found{Style.RESET_ALL}")


def main():
    """Main entry point."""
    colorama_init()

    parser = argparse.ArgumentParser(
        description="FM Manager Save/Load System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                    # List all saves
  %(prog)s info mysave             # Show save details
  %(prog)s create mysave           # Create new save
  %(prog)s load mysave             # Load save
  %(prog)s delete mysave --force   # Delete without confirmation
  %(prog)s rename old new          # Rename save
  %(prog)s auto --enable           # Enable auto-save
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List command
    list_parser = subparsers.add_parser("list", help="List all save files")
    list_parser.set_defaults(func=cmd_list)

    # Info command
    info_parser = subparsers.add_parser("info", help="Show save file information")
    info_parser.add_argument("name", help="Save file name")
    info_parser.set_defaults(func=cmd_info)

    # Create command
    create_parser = subparsers.add_parser("create", help="Create new save")
    create_parser.add_argument("name", help="Save file name")
    create_parser.add_argument("--season", type=int, help="Current season")
    create_parser.add_argument("--week", type=int, help="Current week")
    create_parser.add_argument("--club-id", type=int, help="Player club ID")
    create_parser.set_defaults(func=cmd_create)

    # Load command
    load_parser = subparsers.add_parser("load", help="Load save file")
    load_parser.add_argument("name", help="Save file name")
    load_parser.add_argument(
        "--dry-run", action="store_true", help="Load without restoring to database"
    )
    load_parser.set_defaults(func=cmd_load)

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete save file")
    delete_parser.add_argument("name", help="Save file name")
    delete_parser.add_argument("--force", action="store_true", help="Delete without confirmation")
    delete_parser.set_defaults(func=cmd_delete)

    # Rename command
    rename_parser = subparsers.add_parser("rename", help="Rename save file")
    rename_parser.add_argument("old_name", help="Current save name")
    rename_parser.add_argument("new_name", help="New save name")
    rename_parser.set_defaults(func=cmd_rename)

    # Duplicate command
    dup_parser = subparsers.add_parser("duplicate", help="Duplicate save file")
    dup_parser.add_argument("source", help="Source save name")
    dup_parser.add_argument("new_name", help="New save name")
    dup_parser.set_defaults(func=cmd_duplicate)

    # Auto-save command
    auto_parser = subparsers.add_parser("auto", help="Manage auto-save settings")
    auto_parser.add_argument("--enable", action="store_true", help="Enable auto-save")
    auto_parser.add_argument("--disable", action="store_true", help="Disable auto-save")
    auto_parser.add_argument("--status", action="store_true", help="Show auto-save status")
    auto_parser.add_argument("--interval", type=int, help="Set auto-save interval (minutes)")
    auto_parser.set_defaults(func=cmd_auto)

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create backup of save")
    backup_parser.add_argument("name", help="Save file name")
    backup_parser.set_defaults(func=cmd_backup)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
