#!/usr/bin/env python3
"""生成百万名球员并筛选出高CA/PA球员

Usage:
    python scripts/generate_and_filter_players.py --target 10000 --countries ENG ESP GER FRA ITA
    python scripts/generate_and_filter_players.py --total 1000000 --target 10000 --export-db
"""

import asyncio
import argparse
import time
from typing import Dict, List
from datetime import date

import numpy as np
from sqlalchemy import select

from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.core.models import Player, Position
from fm_manager.engine.youth_batch_generator import (
    CountryYouthGenerator,
    YouthPlayer,
)
from fm_manager.engine.youth_filtering import (
    YouthFilteringPipeline,
    FilteringConfig,
    YouthPlayer as FilterYouthPlayer,
)
from fm_manager.engine.youth_attribute_generator import YouthAttributeGenerator
from fm_manager.config.youth_generation_config import (
    CountryYouthConfig,
    YouthGenerationConfig,
)
from fm_manager.engine.player_generator import PlayerNameGenerator


# 国家配置 - 可以自定义
COUNTRY_CONFIGS = {
    "ENG": CountryYouthConfig(name="England", pool_size=200000, youth_rating=145),  # 英超
    "ESP": CountryYouthConfig(name="Spain", pool_size=180000, youth_rating=140),    # 西甲
    "GER": CountryYouthConfig(name="Germany", pool_size=170000, youth_rating=138),   # 德甲
    "ITA": CountryYouthConfig(name="Italy", pool_size=160000, youth_rating=135),     # 意甲
    "FRA": CountryYouthConfig(name="France", pool_size=150000, youth_rating=132),    # 法甲
    "BRA": CountryYouthConfig(name="Brazil", pool_size=200000, youth_rating=142),    # 巴西
    "ARG": CountryYouthConfig(name="Argentina", pool_size=150000, youth_rating=138), # 阿根廷
    "NED": CountryYouthConfig(name="Netherlands", pool_size=80000, youth_rating=130), # 荷兰
    "POR": CountryYouthConfig(name="Portugal", pool_size=70000, youth_rating=128),   # 葡萄牙
    "BEL": CountryYouthConfig(name="Belgium", pool_size=60000, youth_rating=125),    # 比利时
}


class MillionPlayerGenerator:
    """生成百万名球员并筛选高CA/PA球员的生成器"""
    
    def __init__(
        self,
        countries: List[str],
        target_count: int = 10000,
        total_to_generate: int = 1000000,
        seed: int = 42,
    ):
        self.countries = countries
        self.target_count = target_count
        self.total_to_generate = total_to_generate
        self.seed = seed
        self.attr_gen = YouthAttributeGenerator(seed=seed)
        self.name_gen = PlayerNameGenerator()
        
    def generate_for_country(
        self,
        country_code: str,
        count: int,
    ) -> List[YouthPlayer]:
        """为单个国家生成指定数量的球员"""
        
        config = COUNTRY_CONFIGS.get(country_code, CountryYouthConfig(
            name=country_code,
            pool_size=count,
            youth_rating=120,
        ))
        
        print(f"  生成 {country_code} ({config.name}) 的 {count:,} 名球员...")
        
        generator = CountryYouthGenerator(
            country_code=country_code,
            country_config=config,
            attribute_generator=self.attr_gen,
            seed=self.seed + hash(country_code) % 10000,
        )
        
        players = []
        batch_size = 10000
        
        for i in range(0, count, batch_size):
            current_batch = min(batch_size, count - i)
            
            # Generate raw data
            ages, cas, pas = generator._generate_batch(current_batch)
            positions = generator._generate_positions(current_batch)
            
            # Generate complete players
            batch_players = generator._generate_players_batch(
                ages, cas, pas, positions, config.name
            )
            players.extend(batch_players)
            
            if (i // batch_size) % 10 == 0:
                print(f"    已生成: {i + current_batch:,} / {count:,}")
        
        return players
    
    def generate_all(self) -> Dict[str, List[YouthPlayer]]:
        """为所有国家生成球员"""
        
        print("="*70)
        print(f"开始生成 {self.total_to_generate:,} 名球员...")
        print(f"目标国家: {', '.join(self.countries)}")
        print("="*70)
        
        # 计算每个国家应该生成多少
        players_per_country = self.total_to_generate // len(self.countries)
        
        all_players = {}
        total_generated = 0
        
        for country_code in self.countries:
            players = self.generate_for_country(country_code, players_per_country)
            all_players[country_code] = players
            total_generated += len(players)
            
            # 显示统计
            if players:
                ca_values = [p.current_ability for p in players]
                pa_values = [p.potential_ability for p in players]
                print(f"    CA范围: {min(ca_values):.0f}-{max(ca_values):.0f}, 平均: {np.mean(ca_values):.1f}")
                print(f"    PA范围: {min(pa_values):.0f}-{max(pa_values):.0f}, 平均: {np.mean(pa_values):.1f}")
        
        print(f"\n✅ 总共生成: {total_generated:,} 名球员")
        return all_players
    
    def filter_players(
        self,
        all_players: Dict[str, List[YouthPlayer]],
    ) -> List[YouthPlayer]:
        """筛选出高CA/PA的球员"""
        
        print("\n" + "="*70)
        print("开始筛选高CA/PA球员...")
        print("="*70)
        
        # 将所有球员合并到一个列表
        all_player_list = []
        for country, players in all_players.items():
            for p in players:
                all_player_list.append((country, p))
        
        print(f"待筛选球员总数: {len(all_player_list):,}")
        
        # 按CA排序，取前target_count * 2（给PA筛选留空间）
        all_player_list.sort(key=lambda x: x[1].current_ability, reverse=True)
        ca_filtered = all_player_list[:self.target_count * 2]
        
        print(f"CA筛选后: {len(ca_filtered):,} 名球员")
        
        # 按PA排序，取前target_count
        ca_filtered.sort(key=lambda x: x[1].potential_ability, reverse=True)
        pa_filtered = ca_filtered[:self.target_count]
        
        print(f"PA筛选后: {len(pa_filtered):,} 名球员")
        
        # 转换为YouthPlayer列表
        selected_players = [p for _, p in pa_filtered]
        
        # 显示统计
        if selected_players:
            ca_values = [p.current_ability for p in selected_players]
            pa_values = [p.potential_ability for p in selected_players]
            
            print(f"\n📊 筛选结果统计:")
            print(f"   CA范围: {min(ca_values):.0f} - {max(ca_values):.0f}")
            print(f"   CA平均: {np.mean(ca_values):.1f}")
            print(f"   PA范围: {min(pa_values):.0f} - {max(pa_values):.0f}")
            print(f"   PA平均: {np.mean(pa_values):.1f}")
            
            # 按国家分布
            country_dist = {}
            for country, _ in pa_filtered:
                country_dist[country] = country_dist.get(country, 0) + 1
            
            print(f"\n🌍 国家分布:")
            for country, count in sorted(country_dist.items(), key=lambda x: -x[1]):
                print(f"   {country}: {count:,} 名 ({count/len(selected_players)*100:.1f}%)")
        
        return selected_players
    
    async def save_to_database(self, players: List[YouthPlayer]):
        """保存球员到数据库"""
        
        print("\n" + "="*70)
        print("保存到数据库...")
        print("="*70)
        
        await init_db()
        session_maker = get_session_maker()
        
        async with session_maker() as session:
            # 清空现有球员（可选）
            # result = await session.execute(select(Player))
            # for p in result.scalars():
            #     await session.delete(p)
            # await session.commit()
            
            # 批量添加新球员
            batch_size = 1000
            total_saved = 0
            
            for i in range(0, len(players), batch_size):
                batch = players[i:i+batch_size]
                
                for youth_player in batch:
                    db_player = youth_player.to_player()
                    session.add(db_player)
                
                await session.commit()
                total_saved += len(batch)
                
                if (i // batch_size) % 5 == 0:
                    print(f"  已保存: {total_saved:,} / {len(players):,}")
            
            print(f"✅ 成功保存 {total_saved:,} 名球员到数据库")
        
        await close_db()
    
    def save_to_csv(self, players: List[YouthPlayer], filepath: str = "data/top_players.csv"):
        """保存球员到CSV文件"""
        
        import csv
        
        print(f"\n保存到CSV: {filepath}")
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow([
                'ID', 'First Name', 'Last Name', 'Full Name', 'Nationality',
                'Position', 'Age', 'Current Ability', 'Potential Ability',
                'Pace', 'Shooting', 'Passing', 'Dribbling', 'Tackling', 'Marking'
            ])
            
            # 写入数据
            for i, player in enumerate(players, 1):
                attrs = player.attributes
                writer.writerow([
                    i,
                    player.first_name,
                    player.last_name,
                    player.full_name,
                    player.nationality,
                    player.position.value,
                    player.age,
                    player.current_ability,
                    player.potential_ability,
                    attrs.get('pace', 0),
                    attrs.get('shooting', 0),
                    attrs.get('passing', 0),
                    attrs.get('dribbling', 0),
                    attrs.get('tackling', 0),
                    attrs.get('marking', 0),
                ])
        
        print(f"✅ 成功保存 {len(players):,} 名球员到 {filepath}")


async def main():
    parser = argparse.ArgumentParser(
        description="生成百万名球员并筛选高CA/PA球员"
    )
    parser.add_argument(
        "--countries",
        nargs="+",
        default=["ENG", "ESP", "GER", "FRA", "ITA", "BRA", "ARG"],
        help="国家代码列表 (默认: ENG ESP GER FRA ITA BRA ARG)",
    )
    parser.add_argument(
        "--total",
        type=int,
        default=10000000,
        help="总共生成的球员数量 (默认: 1,000,000)",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=10000,
        help="筛选后保留的球员数量 (默认: 10,000)",
    )
    parser.add_argument(
        "--export-db",
        action="store_true",
        help="导出到数据库",
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        default="data/top_players.csv",
        help="导出到CSV文件路径",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子 (默认: 42)",
    )
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    # 创建生成器
    generator = MillionPlayerGenerator(
        countries=args.countries,
        target_count=args.target,
        total_to_generate=args.total,
        seed=args.seed,
    )
    
    # 生成球员
    all_players = generator.generate_all()
    
    # 筛选球员
    selected_players = generator.filter_players(all_players)
    
    # 导出
    if args.export_db:
        await generator.save_to_database(selected_players)
    
    if args.export_csv:
        generator.save_to_csv(selected_players, args.export_csv)
    
    # 完成统计
    elapsed = time.time() - start_time
    print("\n" + "="*70)
    print("完成!")
    print("="*70)
    print(f"总用时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
    print(f"生成速度: {args.total/elapsed:.0f} 球员/秒")
    print(f"筛选比例: {len(selected_players)/args.total*100:.2f}%")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
