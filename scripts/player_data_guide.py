#!/usr/bin/env python3
"""完整的球员数据使用指南

Usage:
    python scripts/player_data_guide.py
"""


def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def guide_generate_players():
    """指南1: 生成球员"""
    print_section("指南1: 生成大规模球员数据")
    
    print("""
使用 massive_player_generator.py 生成海量球员:

1. 生成100万球员，保留前0.1% (1,000名):
   python scripts/massive_player_generator.py --total 1000000 --top-percent 0.1

2. 生成1亿球员，保留前0.1% (100,000名):
   python scripts/massive_player_generator.py --total 100000000 --top-percent 0.1

3. 自定义国家和输出位置:
   python scripts/massive_player_generator.py \\
       --total 10000000 \\
       --top-percent 0.1 \\
       --countries ENG ESP GER FRA ITA BRA ARG \\
       --output data/my_players

参数说明:
   --total: 总共生成的球员数量
   --top-percent: 保留的顶级球员百分比 (默认0.1%)
   --countries: 国家代码列表
   --output: 输出目录
   --seed: 随机种子 (用于可复现性)

特性:
   - 使用 NumPy 向量化，速度 >200万球员/秒
   - 使用 fm_manager/engine/player_generator.py 的名字生成器
   - 支持15个国家，50+姓名库
   - 内存效率高 (<500MB峰值)
""")


def guide_use_npz():
    """指南2: 使用NPZ文件"""
    print_section("指南2: 使用生成的NPZ数据文件")
    
    print("""
文件格式:
   生成的数据保存在 .npz 文件中，这是一种 NumPy 压缩格式
   包含以下数组:
   - ca: 当前能力 (Current Ability), shape=(N,), dtype=int16
   - pa: 潜力 (Potential Ability), shape=(N,), dtype=int16
   - country_idx: 国家索引, shape=(N,), dtype=int16
   - age: 年龄, shape=(N,), dtype=int16
   - height: 身高(cm), shape=(N,), dtype=int16
   - weight: 体重(kg), shape=(N,), dtype=int16

基本用法:

   import numpy as np

   # 1. 加载数据
   data = np.load('data/massive_players_100m/top_players.npz')
   
   # 2. 访问数据
   ca_values = data['ca']      # 获取所有CA值
   pa_values = data['pa']      # 获取所有PA值
   
   # 3. 访问单个球员
   player_0_ca = data['ca'][0]
   player_0_pa = data['pa'][0]

常用操作:

   # 筛选 PA > 180 的天才球员
   mask = data['pa'] > 180
   elite_indices = np.where(mask)[0]
   
   # 按PA排序，取前100名
   top_100_indices = np.argsort(-data['pa'])[:100]
   
   # 计算统计信息
   avg_ca = np.mean(data['ca'])
   avg_pa = np.mean(data['pa'])
   
   # 按国家分组统计
   countries = ['ENG', 'ESP', 'GER', ...]
   for i, country in enumerate(countries):
       mask = data['country_idx'] == i
       if np.any(mask):
           avg_ca = np.mean(data['ca'][mask])
           print(f"{country}: 平均CA={avg_ca:.1f}")

内存优化:
   
   # 对于超大文件，使用内存映射模式
   data = np.load('huge_file.npz', mmap_mode='r')
   # 这样只会加载需要的数据到内存
""")


def guide_integrate_to_game():
    """指南3: 集成到游戏"""
    print_section("指南3: 将数据集成到游戏引擎")
    
    print("""
将生成的球员数据转换为 Player 模型:

   import numpy as np
   from fm_manager.core.models import Player, Position
   
   # 加载数据
   data = np.load('data/massive_players_100m/top_players.npz')
   
   # 国家代码映射
   countries = ['ENG', 'ESP', 'GER', 'ITA', 'FRA', 'BRA', 'ARG', 
                'POR', 'NED', 'BEL', 'CHN', 'JPN', 'KOR', 'USA', 'MEX']
   
   # 位置映射 (简化版)
   position_map = {
       0: Position.GK,   # 根据你的索引定义
       1: Position.CB,
       # ... 其他位置
   }
   
   # 转换为 Player 对象
   players = []
   for i in range(min(1000, len(data['ca']))):  # 取前1000名
       # 解析名字 (使用名字生成器)
       country_idx = data['country_idx'][i]
       country_name = countries[country_idx]
       
       player = Player(
           id=i,
           first_name=f"Player_{i}",  # 或使用名字生成器
           last_name=country_name,
           nationality=country_name,
           position=Position.ST,  # 根据 country_idx 或随机分配
           current_ability=int(data['ca'][i]),
           potential_ability=int(data['pa'][i]),
           age=int(data['age'][i]),
           height=int(data['height'][i]),
           weight=int(data['weight'][i]),
       )
       players.append(player)

批量导入到数据库:

   import asyncio
   from fm_manager.core import init_db, get_session_maker
   
   async def import_players():
       await init_db()
       session_maker = get_session_maker()
       
       async with session_maker() as session:
           for player in players:
               session.add(player)
           await session.commit()
       
       print(f"导入完成: {len(players)} 名球员")
   
   asyncio.run(import_players())
""")


def guide_filtering_strategies():
    """指南4: 筛选策略"""
    print_section("指南4: 不同的球员筛选策略")
    
    print("""
策略1: 平衡型 (当前使用)
   评分 = CA * 0.4 + PA * 0.6
   优点: 平衡即战力和潜力
   适用: 一般俱乐部招募

策略2: 即战力优先
   评分 = CA * 0.8 + PA * 0.2
   优点: 选出的球员立即可用
   适用: 争夺冠军的球队

策略3: 潜力优先
   评分 = CA * 0.2 + PA * 0.8
   优点: 发现未来之星
   适用: 青训导向的俱乐部

策略4: 投资回报
   评分 = (PA - CA) * 2 + CA * 0.5
   优点: 选出成长空间最大的球员
   适用: 低预算俱乐部转售盈利

策略5: 复合指标
   考虑年龄因素:
   评分 = CA * 0.3 + PA * 0.5 + (21 - age) * 2
   优点: 优先考虑年轻球员
   适用: 长期建队计划

实现示例:

   def calculate_score(ca, pa, age, strategy='balanced'):
       if strategy == 'balanced':
           return ca * 0.4 + pa * 0.6
       elif strategy == 'current':
           return ca * 0.8 + pa * 0.2
       elif strategy == 'potential':
           return ca * 0.2 + pa * 0.8
       elif strategy == 'roi':
           return (pa - ca) * 2 + ca * 0.5
       elif strategy == 'youth':
           return ca * 0.3 + pa * 0.5 + max(0, 21 - age) * 2
""")


def guide_performance_tips():
    """指南5: 性能优化"""
    print_section("指南5: 性能优化技巧")
    
    print("""
生成阶段优化:

1. 批处理大小
   默认 1,000,000 球员/批是最佳平衡点
   更大批次不会显著提高速度，但会增加内存

2. 两阶段策略
   Pass 1: 只生成 CA/PA，用堆筛选 (内存 O(target) 而非 O(total))
   Pass 2: 只为选中球员生成完整数据
   这样处理1亿球员也只需要 <500MB 内存

3. 向量化操作
   所有计算使用 NumPy 向量化
   避免 Python 循环
   速度提升: 100-1000倍

数据加载优化:

1. 内存映射 (mmap)
   data = np.load('huge.npz', mmap_mode='r')
   适合超大文件 (>1GB)

2. 分块处理
   如果数据太大无法一次加载:
   
   chunk_size = 10000
   for i in range(0, len(data['ca']), chunk_size):
       chunk_ca = data['ca'][i:i+chunk_size]
       chunk_pa = data['pa'][i:i+chunk_size]
       # 处理这一块数据

3. 选择性加载
   如果只需要 CA 和 PA:
   data = np.load('file.npz')
   ca = data['ca']  # 只加载这个数组到内存

预期性能:

   生成1亿球员:
   - 时间: ~40 秒
   - 内存: < 500 MB
   - 输出: ~1 MB (10万名顶级球员)
   
   生成10亿球员:
   - 时间: ~7-8 分钟
   - 内存: < 1 GB
   - 输出: ~10 MB (100万名顶级球员)
""")


def main():
    print("\n" + "=" * 80)
    print("足球经理 - 大规模球员生成系统使用指南")
    print("=" * 80)
    print("\n本文档介绍如何使用高性能球员生成器和数据文件")
    
    guide_generate_players()
    guide_use_npz()
    guide_integrate_to_game()
    guide_filtering_strategies()
    guide_performance_tips()
    
    print_section("总结")
    print("""
关键文件:
   - scripts/massive_player_generator.py: 生成器主程序
   - scripts/demo_use_npz_data.py: NPZ文件使用演示
   - data/massive_players_100m/top_players.npz: 示例数据 (10万名顶级球员)

特点:
   ✅ 每秒生成 200万+ 球员
   ✅ 内存使用 < 500MB (即使生成1亿球员)
   ✅ 使用 fm_manager/engine 的名字生成器
   ✅ 高效的 top-k 筛选算法
   ✅ 标准化 NPZ 格式，易于使用

支持的国家:
   ENG (英格兰), ESP (西班牙), GER (德国), ITA (意大利), FRA (法国),
   BRA (巴西), ARG (阿根廷), POR (葡萄牙), NED (荷兰), BEL (比利时),
   CHN (中国), JPN (日本), KOR (韩国), USA (美国), MEX (墨西哥)

更多帮助:
   python scripts/massive_player_generator.py --help
   python scripts/demo_use_npz_data.py
""")


if __name__ == "__main__":
    main()
