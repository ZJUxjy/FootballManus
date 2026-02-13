#!/usr/bin/env python3
"""List all columns in data/players_en.csv

Usage:
    python scripts/list_csv_columns.py
"""

import pandas as pd


def main():
    # Read CSV file
    csv_path = "data/players_en.csv"
    df = pd.read_csv(csv_path, encoding="latin-1", sep=";")

    print("=" * 80)
    print(f"CSV File: {csv_path}")
    print(f"Total Rows: {len(df):,}")
    print(f"Total Columns: {len(df.columns)}")
    print("=" * 80)
    print()

    # List all columns with index
    print("All Columns:")
    print("-" * 80)
    for i, col in enumerate(df.columns, 1):
        print(f"{i:2}. {col}")

    print()
    print("=" * 80)

    # Categorize columns
    print("\nColumn Categories:")
    print("=" * 80)

    # Basic info
    basic_cols = ["Name", "Nation", "Position", "Club", "Age", "Date Of Birth", "Based"]
    print("\n1. Basic Information:")
    for col in basic_cols:
        if col in df.columns:
            print(f"   - {col}")

    # Status/Condition
    status_cols = ["Fitness", "Con", "Happiness Level", "Jdns", "Mtc Exc"]
    print("\n2. Status & Condition:")
    for col in status_cols:
        if col in df.columns:
            print(f"   - {col}")

    # International
    intl_cols = ["Int Caps", "Int Goals"]
    print("\n3. International Career:")
    for col in intl_cols:
        if col in df.columns:
            print(f"   - {col}")

    # Financial
    financial_cols = ["Wage", "Value", "Sale Value", "Minimum Fee"]
    print("\n4. Financial:")
    for col in financial_cols:
        if col in df.columns:
            print(f"   - {col}")

    # Ratings
    rating_cols = [col for col in df.columns if "Rating" in col and "Pot" not in col]
    print(f"\n5. Position Ratings ({len(rating_cols)} columns):")
    for col in rating_cols:
        print(f"   - {col}")

    # Potential Ratings
    pot_cols = [col for col in df.columns if "Pot Rating" in col]
    print(f"\n6. Potential Ratings ({len(pot_cols)} columns):")
    for col in pot_cols:
        print(f"   - {col}")

    # Club/League
    club_cols = ["Division", "Squad", "Squad Rep", "Club ID"]
    print("\n7. Club & League:")
    for col in club_cols:
        if col in df.columns:
            print(f"   - {col}")

    # Contract
    contract_cols = [
        "Contract Type",
        "Joined Club",
        "Contract End",
        "Squad Status",
        "Perceived Squad Status",
        "Transfer Status",
    ]
    print("\n8. Contract & Status:")
    for col in contract_cols:
        if col in df.columns:
            print(f"   - {col}")

    # IDs
    id_cols = ["Unique ID", "Club ID"]
    print("\n9. Identifiers:")
    for col in id_cols:
        if col in df.columns:
            print(f"   - {col}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
