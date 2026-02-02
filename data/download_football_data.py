#!/usr/bin/env python3

import os
import requests
import zipfile
import sqlite3
import csv
import json
from pathlib import Path


class FootballDataDownloader:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def download_from_github(self, repo_url, file_name, output_name=None):
        if not output_name:
            output_name = file_name.split("/")[-1]

        output_path = self.data_dir / output_name

        if output_path.exists():
            print(f"✓ 文件已存在: {output_path}")
            return output_path

        raw_url = f"https://raw.githubusercontent.com/{repo_url}/{file_name}"
        print(f"正在下载: {raw_url}")

        try:
            response = requests.get(raw_url, stream=True, timeout=30)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"✓ 下载完成: {output_path}")
            return output_path

        except Exception as e:
            print(f"✗ 下载失败: {e}")
            return None

    def download_transfermarkt_data(self):
        print("\n=== Transfermarkt 数据集下载说明 ===")
        print("数据源: salimt/football-datasets (93K+ 球员)")
        print("\n该数据集主要托管在 Kaggle，需要手动下载：")
        print("\nURL: https://www.kaggle.com/datasets/xfkzujqjvx97n/football-datasets")
        print("\n下载步骤:")
        print("1. 访问上述 Kaggle 链接")
        print("2. 登录并下载数据集 (约 85MB)")
        print("3. 解压后找到以下文件:")
        print("   - player_profiles.csv")
        print("   - player_performances.csv")
        print("   - clubs.csv")
        print("4. 将文件重命名并复制到 data/ 文件夹:")
        print("   player_profiles.csv -> transfermarkt_player_profiles.csv")
        print("   player_performances.csv -> transfermarkt_player_performances.csv")
        print("   clubs.csv -> transfermarkt_clubs.csv")
        print("\n数据覆盖:")
        print("  - 92,671 名球员")
        print("  - 2,175 家俱乐部")
        print("  - 1,878,719 条出场记录")
        print("  - 市场价值、转会历史、伤病记录等")

    def download_football_db(self):
        print("\n=== Openfootball 数据集下载说明 ===")
        print("数据源: openfootball/football.json (五大联赛)")
        print("\n该数据集需要从GitHub克隆或手动下载JSON文件：")
        print("\nURL: https://github.com/openfootball/football.json")
        print("\n可用联赛:")
        print("  - england (英超)")
        print("  - germany (德甲)")
        print("  - italy (意甲)")
        print("  - spain (西甲)")
        print("  - france (法甲)")
        print("\n可用赛季: 2023-24, 2024-25, 2025-26")
        print("\nJSON文件路径示例:")
        print(
            "  - https://raw.githubusercontent.com/openfootball/football.json/master/england/2023-24/1-premierleague.json"
        )
        print("\n或者使用 fbtxt2json 工具转换:")
        print("  - 从Football.TXT格式转换为JSON")
        print("  - 工具: https://github.com/openfootball/football.db")

    def download_statsbomb_sample(self):
        print("\n=== 下载 StatsBomb Open Data 样本 ===")
        print("数据源: statsbomb/open-data (事件级数据)")

        repo = "statsbomb/open-data"
        files = [
            "data/3788747.json",
            "data/matches/2/37646.json",
            "lineups/3788747.json",
        ]

        for file in files:
            output_name = f"statsbomb_{file.replace('/', '_')}"
            self.download_from_github(repo, file, output_name)

        print(f"\n✓ StatsBomb 样本数据已下载到: {self.data_dir}")

    def download_kaggle_instructions(self):
        print("\n=== Kaggle 数据集下载说明 ===")
        print("\n由于Kaggle需要API认证，请手动下载以下数据集：")
        print("\n1. EA Sports FC 24 Complete Player Dataset:")
        print(
            "   URL: https://www.kaggle.com/datasets/stefanoleone992/ea-sports-fc-24-complete-player-dataset"
        )
        print("   下载后解压，将 male_players.csv 复制到 data/ 文件夹")
        print("   数据量: 17,326+ 球员, 48个属性")
        print("\n2. Football Players Stats (2024-2025):")
        print(
            "   URL: https://www.kaggle.com/datasets/georgescristianpopescu/football-players-stats-2024-2025"
        )
        print("   下载后解压，将 CSV 文件复制到 data/ 文件夹")
        print("\n3. 5.7M+ Records - Most Comprehensive Football Dataset:")
        print("   URL: https://www.kaggle.com/datasets/xfkzujqjvx97n/football-datasets")
        print("   这是Transfermarkt数据集，包含93K+球员")
        print("   下载后找到: player_profiles.csv, clubs.csv, player_performances.csv")
        print("   重命名为: transfermarkt_player_profiles.csv 等")
        print("\n4. Club Football Match Data (2000-2025):")
        print("   URL: https://www.kaggle.com/datasets/adamgbor/club-football-match-data-2000-2025")
        print("   下载后解压，将 CSV 文件复制到 data/ 文件夹")
        print("   主要文件: male_players.csv")
        print("\n2. Football Players Stats (2025-2026):")
        print(
            "   URL: https://www.kaggle.com/datasets/georgescristianpopescu/football-players-stats-2024-2025"
        )
        print("   下载后解压，将 .csv 文件放到 data/ 文件夹")
        print("\n3. Club Football Match Data (2000-2025):")
        print("   URL: https://www.kaggle.com/datasets/adamgbor/club-football-match-data-2000-2025")
        print("   下载后解压，将 .csv 文件放到 data/ 文件夹")

    def show_menu(self):
        print("\n" + "=" * 50)
        print("    足球数据下载器 - 选择数据源")
        print("=" * 50)
        print("1. Transfermarkt 数据集 (CSV, 93K+ 球员)")
        print("2. Openfootball 赛程数据 (JSON, 五大联赛)")
        print("3. StatsBomb Open Data (JSON, 事件级数据)")
        print("4. Kaggle 数据集 (CSV, 需手动下载, 推荐)")
        print("0. 退出")
        print("=" * 50)

        choice = input("\n请选择 (0-4): ").strip()

        if choice == "1":
            self.download_transfermarkt_data()
        elif choice == "2":
            self.download_football_db()
        elif choice == "3":
            self.download_statsbomb_sample()
        elif choice == "4":
            self.download_kaggle_instructions()
        elif choice == "0":
            print("退出")
            return False
        else:
            print("无效选择")

        return True

    def run(self):
        print("\n📊 足球数据下载器")
        print(f"数据保存目录: {self.data_dir.absolute()}")

        while True:
            if not self.show_menu():
                break


if __name__ == "__main__":
    import sys

    downloader = FootballDataDownloader()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--transfermarkt":
            downloader.download_transfermarkt_data()
        elif command == "--football-db":
            downloader.download_football_db()
        elif command == "--statsbomb":
            downloader.download_statsbomb_sample()
        elif command == "--kaggle":
            downloader.download_kaggle_instructions()
        elif command == "--help" or command == "-h":
            print("足球数据下载器")
            print("\n用法:")
            print("  python download_football_data.py              # 交互式菜单")
            print("  python download_football_data.py --transfermarkt  # Transfermarkt数据集说明")
            print("  python download_football_data.py --football-db   # Openfootball数据集说明")
            print("  python download_football_data.py --statsbomb     # StatsBomb样本")
            print("  python download_football_data.py --kaggle       # Kaggle数据集说明")
        else:
            print(f"未知命令: {command}")
            print("使用 --help 查看帮助")
    else:
        downloader.run()
