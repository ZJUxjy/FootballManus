#!/usr/bin/env python3
"""演示如何使用生成的球员数据 (NPZ文件)

Usage:
    python scripts/demo_use_npz_data.py
"""

import numpy as np
import json
from pathlib import Path


def load_players_data(filepath: str = "data/massive_players_100m/top_players.npz"):
    """加载球员数据"""
    data = np.load(filepath)
    with open(filepath.replace("top_players.npz", "stats.json")) as f:
        stats = json.load(f)
    return data, stats


def demonstrate_basic_usage():
    """演示基本用法"""
    print("=" * 70)
    print("演示1: 基本用法 - 加载和查看数据")
    print("=" * 70)
    
    # 加载数据
    data, stats = load_players_data()
    
    print(f"\n📊 数据集统计:")
    print(f"   总生成: {stats['total_generated']:,} 球员")
    print(f"   选中: {stats['selected']:,} 球员")
    
    print(f"\n📁 数据包含以下数组:")
    for key in data.files:
        arr = data[key]
        print(f"   {key}: {arr.shape} ({arr.dtype})")
    
    # 访问单个球员
    print(f"\n👤 第1名球员的信息:")
    print(f"   CA: {data['ca'][0]}")
    print(f"   PA: {data['pa'][0]}")
    print(f"   国家索引: {data['country_idx'][0]}")
    print(f"   年龄: {data['age'][0]}")
    print(f"   身高: {data['height'][0]}cm")
    print(f"   体重: {data['weight'][0]}kg")


def demonstrate_filtering():
    """演示如何筛选球员"""
    print("\n" + "=" * 70)
    print("演示2: 筛选球员 - 找出PA > 180的天才")
    print("=" * 70)
    
    data, _ = load_players_data()
    
    # 筛选 PA > 180 的球员
    mask = data['pa'] > 180
    elite_indices = np.where(mask)[0]
    
    print(f"\n🌟 发现 {len(elite_indices)} 名天才球员 (PA > 180)")
    
    # 显示前10名
    print(f"\n前10名天才球员:")
    for i, idx in enumerate(elite_indices[:10], 1):
        print(f"   {i}. CA: {data['ca'][idx]:3d}, PA: {data['pa'][idx]:3d}, "
              f"Age: {data['age'][idx]:2d}, Height: {data['height'][idx]:3d}cm")


def demonstrate_sorting():
    """演示如何排序"""
    print("\n" + "=" * 70)
    print("演示3: 排序 - PA最高的前20名球员")
    print("=" * 70)
    
    data, _ = load_players_data()
    
    # 按PA排序，取前20
    sorted_indices = np.argsort(-data['pa'])[:20]
    
    print(f"\n🏆 PA Top 20:")
    for i, idx in enumerate(sorted_indices, 1):
        print(f"   {i:2d}. CA: {data['ca'][idx]:3d}, PA: {data['pa'][idx]:3d}, "
              f"Age: {data['age'][idx]:2d}")


def demonstrate_statistics():
    """演示统计分析"""
    print("\n" + "=" * 70)
    print("演示4: 统计分析 - 按国家分组统计")
    print("=" * 70)
    
    data, _ = load_players_data()
    
    # 国家代码映射
    countries = ['ENG', 'ESP', 'GER', 'ITA', 'FRA', 'BRA', 'ARG', 'POR', 'NED', 'BEL', 
                 'CHN', 'JPN', 'KOR', 'USA', 'MEX']
    
    # 按国家统计
    print(f"\n🌍 各国平均CA/PA:")
    for i, country in enumerate(countries):
        mask = data['country_idx'] == i
        if np.any(mask):
            avg_ca = np.mean(data['ca'][mask])
            avg_pa = np.mean(data['pa'][mask])
            count = np.sum(mask)
            print(f"   {country}: 平均CA={avg_ca:5.1f}, 平均PA={avg_pa:5.1f}, 人数={count:,}")


def demonstrate_export_to_csv():
    """演示导出到CSV"""
    print("\n" + "=" * 70)
    print("演示5: 导出到CSV")
    print("=" * 70)
    
    data, _ = load_players_data()
    
    # 导出前1000名到CSV
    output_file = "data/top_1000_players_export.csv"
    
    # 按PA排序，取前1000
    top_indices = np.argsort(-data['pa'])[:1000]
    
    import csv
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Rank', 'CA', 'PA', 'Country', 'Age', 'Height', 'Weight'])
        
        countries = ['ENG', 'ESP', 'GER', 'ITA', 'FRA', 'BRA', 'ARG', 'POR', 'NED', 'BEL', 
                     'CHN', 'JPN', 'KOR', 'USA', 'MEX']
        
        for rank, idx in enumerate(top_indices, 1):
            country_idx = data['country_idx'][idx]
            country = countries[country_idx] if country_idx < len(countries) else f"IDX_{country_idx}"
            
            writer.writerow([
                rank,
                int(data['ca'][idx]),
                int(data['pa'][idx]),
                country,
                int(data['age'][idx]),
                int(data['height'][idx]),
                int(data['weight'][idx]),
            ])
    
    print(f"✅ 已导出前1000名球员到: {output_file}")


def demonstrate_memory_efficiency():
    """演示内存效率"""
    print("\n" + "=" * 70)
    print("演示6: 内存效率 - 处理大数据集")
    print("=" * 70)
    
    data, stats = load_players_data()
    
    # 计算内存使用
    total_bytes = sum(arr.nbytes for arr in data.values())
    print(f"\n💾 内存使用情况:")
    print(f"   总大小: {total_bytes / 1024 / 1024:.2f} MB")
    print(f"   每名球员: {total_bytes / len(data['ca']):.1f} 字节")
    
    # 演示内存映射 (mmap) - 对于更大的文件很有用
    print(f"\n📖 内存映射模式 (用于超大文件):")
    print(f"   np.load('file.npz', mmap_mode='r')")
    print(f"   这样只加载需要的部分到内存")


def main():
    """运行所有演示"""
    print("\n" + "=" * 70)
    print("NPZ数据文件使用演示")
    print("=" * 70)
    print("\n这个脚本展示如何使用生成的球员数据文件")
    print("文件位置: data/massive_players_100m/top_players.npz")
    print()
    
    demonstrate_basic_usage()
    demonstrate_filtering()
    demonstrate_sorting()
    demonstrate_statistics()
    demonstrate_export_to_csv()
    demonstrate_memory_efficiency()
    
    print("\n" + "=" * 70)
    print("演示完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
