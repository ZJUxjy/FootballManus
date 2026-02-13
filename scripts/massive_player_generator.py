#!/usr/bin/env python3
"""Ultra-high performance player generator for massive scale.

Generates 100M+ players efficiently using NumPy vectorization and streaming.
Keeps top 0.1% by both CA and PA using a two-pass filtering strategy.

Usage:
    python scripts/massive_player_generator.py --total 100000000 --top-percent 0.1
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import time
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import heapq

from fm_manager.engine.player_generator import PlayerNameGenerator


@dataclass
class CountryConfig:
    """Country configuration for name generation."""
    code: str
    name: str
    weight: float  # Population/football weight
    name_lists: Tuple[List[str], List[str]]  # (first_names, last_names)


# Country configurations - using engine's PlayerNameGenerator for names
# Only need code, name, and weight - names come from PlayerNameGenerator
COUNTRIES = {
    "ENG": ("England", 0.08),
    "ESP": ("Spain", 0.07),
    "GER": ("Germany", 0.07),
    "ITA": ("Italy", 0.06),
    "FRA": ("France", 0.06),
    "BRA": ("Brazil", 0.12),
    "ARG": ("Argentina", 0.08),
    "POR": ("Portugal", 0.04),
    "NED": ("Netherlands", 0.04),
    "BEL": ("Belgium", 0.03),
    "CHN": ("China", 0.15),
    "JPN": ("Japan", 0.05),
    "KOR": ("South Korea", 0.04),
    "USA": ("United States", 0.06),
    "MEX": ("Mexico", 0.06),
}


class MassivePlayerGenerator:
    """High-performance player generator for 100M+ scale."""
    
    def __init__(
        self,
        total_players: int = 100_000_000,
        top_percent: float = 0.1,
        seed: int = 42,
    ):
        self.total_players = total_players
        self.target_count = int(total_players * top_percent / 100)
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        
        # Setup country weights and arrays for vectorized selection
        self.country_codes = list(COUNTRIES.keys())
        self.country_weights = np.array([COUNTRIES[c][1] for c in self.country_codes])
        self.country_weights /= self.country_weights.sum()
        
    def generate_batch(self, batch_size: int, batch_idx: int) -> Dict[str, np.ndarray]:
        """Generate a batch of players using pure NumPy.
        
        Returns dict with arrays: ca, pa, country_idx, age, height, weight
        """
        # Use different seed for each batch
        batch_rng = np.random.default_rng(self.seed + batch_idx)
        
        # Generate CA/PA using normal distribution
        # CA: mean=55, std=15, clipped to [20, 100]
        ca = batch_rng.normal(55, 10, batch_size)
        ca = np.clip(ca, 20, 120).astype(np.int16)
        
        # PA: mean=70, std=25, clipped to [30, 200]
        pa = batch_rng.normal(70, 12, batch_size)
        pa = np.clip(pa, 30, 200).astype(np.int16)
        
        # Ensure PA >= CA * 1.2
        min_pa = (ca * 1.2).astype(np.int16)
        pa = np.maximum(pa, min_pa)
        pa = np.clip(pa, ca, 200).astype(np.int16)
        
        # Assign countries (vectorized)
        country_idx = batch_rng.choice(
            len(self.country_codes),
            size=batch_size,
            p=self.country_weights
        ).astype(np.int16)
        
        # Generate ages (14-21, weighted toward 16-18)
        age = batch_rng.normal(16, 2, batch_size)
        age = np.clip(age, 14, 21).astype(np.int16)
        
        # Generate physical attributes based on position
        height = batch_rng.normal(175, 10, batch_size)
        height = np.clip(height, 160, 200).astype(np.int16)
        
        weight = batch_rng.normal(70, 10, batch_size)
        weight = np.clip(weight, 50, 110).astype(np.int16)
        
        return {
            'ca': ca,
            'pa': pa,
            'country_idx': country_idx,
            'age': age,
            'height': height,
            'weight': weight,
        }
    
    def generate_names(self, country_indices: np.ndarray, count: int) -> List[str]:
        """Generate names for selected players using PlayerNameGenerator."""
        name_gen = PlayerNameGenerator()
        full_names = []
        
        for idx in country_indices:
            country_name = COUNTRIES[self.country_codes[idx]][0]
            name = name_gen.generate_name(country_name)
            full_names.append(name)
        
        return full_names
    
    def run_two_pass_generation(self) -> Tuple[np.ndarray, Dict]:
        """Two-pass generation: first pass collect candidates, second pass generate full data.
        
        Returns: (selected_indices, stats)
        """
        print("=" * 80)
        print(f"MASSIVE PLAYER GENERATION")
        print("=" * 80)
        print(f"Total to generate: {self.total_players:,}")
        print(f"Target to keep: {self.target_count:,} (top {self.target_count/self.total_players*100:.2f}%)")
        print(f"Batch size: 1,000,000")
        print("=" * 80)
        
        start_time = time.time()
        batch_size = 1_000_000
        num_batches = (self.total_players + batch_size - 1) // batch_size
        
        # PASS 1: Collect CA and PA, maintain top candidates
        print("\n📊 PASS 1: Collecting top candidates by CA and PA...")
        
        # Use a min-heap to keep top candidates efficiently
        heap_size = self.target_count * 2
        top_heap = []
        
        # Collect histogram data for ALL generated players
        all_ca_hist = np.zeros(201, dtype=np.int64)  # CA range: 0-200
        all_pa_hist = np.zeros(201, dtype=np.int64)  # PA range: 0-200
        all_country_hist = np.zeros(len(self.country_codes), dtype=np.int64)
        
        for batch_idx in range(num_batches):
            current_batch_size = min(batch_size, self.total_players - batch_idx * batch_size)
            
            # Generate batch
            batch_data = self.generate_batch(current_batch_size, batch_idx)
            ca = batch_data['ca']
            pa = batch_data['pa']
            country_idx = batch_data['country_idx']
            
            # Update histograms for ALL players
            for ca_val in ca:
                if 0 <= ca_val <= 200:
                    all_ca_hist[ca_val] += 1
            for pa_val in pa:
                if 0 <= pa_val <= 200:
                    all_pa_hist[pa_val] += 1
            for c_idx in country_idx:
                if 0 <= c_idx < len(self.country_codes):
                    all_country_hist[c_idx] += 1
            
            # Calculate composite score
            score = ca * 0.4 + pa * 0.6
            
            # Add to heap (top candidates)
            for local_idx in range(current_batch_size):
                ca_val = int(ca[local_idx])
                pa_val = int(pa[local_idx])
                score_val = score[local_idx]
                
                if len(top_heap) < heap_size:
                    heapq.heappush(top_heap, (score_val, ca_val, pa_val, batch_idx, local_idx))
                elif score_val > top_heap[0][0]:
                    heapq.heapreplace(top_heap, (score_val, ca_val, pa_val, batch_idx, local_idx))
            
            if (batch_idx + 1) % 10 == 0 or batch_idx == num_batches - 1:
                elapsed = time.time() - start_time
                progress = (batch_idx + 1) / num_batches * 100
                speed = (batch_idx + 1) * batch_size / elapsed
                print(f"  Batch {batch_idx + 1}/{num_batches} ({progress:.1f}%) | "
                      f"Speed: {speed:,.0f} players/sec | "
                      f"Top CA: {max([x[1] for x in top_heap]):.0f} | "
                      f"Top PA: {max([x[2] for x in top_heap]):.0f}")
        
        # Extract top candidates
        candidates = sorted(top_heap, key=lambda x: -(x[1] * 0.4 + x[2] * 0.6))[:self.target_count]
        
        print(f"\n✅ PASS 1 Complete: {len(candidates):,} candidates selected")
        print(f"   CA range: {min([x[1] for x in candidates]):.0f} - {max([x[1] for x in candidates]):.0f}")
        print(f"   PA range: {min([x[2] for x in candidates]):.0f} - {max([x[2] for x in candidates]):.0f}")
        
        # Store histograms for visualization
        self.all_ca_hist = all_ca_hist
        self.all_pa_hist = all_pa_hist
        self.all_country_hist = all_country_hist
        
        # PASS 2: Regenerate full data for selected candidates
        print("\n📊 PASS 2: Generating full player data for selected candidates...")
        
        # Group candidates by batch for efficient regeneration
        batch_to_indices = {}
        for _, _, _, batch_idx, local_idx in candidates:
            if batch_idx not in batch_to_indices:
                batch_to_indices[batch_idx] = []
            batch_to_indices[batch_idx].append(local_idx)
        
        # Generate full data for selected players
        selected_data = {
            'ca': [],
            'pa': [],
            'country_idx': [],
            'age': [],
            'height': [],
            'weight': [],
        }
        
        for batch_idx, local_indices in sorted(batch_to_indices.items()):
            # Regenerate this batch
            batch_size = min(1_000_000, self.total_players - batch_idx * 1_000_000)
            batch_data = self.generate_batch(batch_size, batch_idx)
            
            # Extract selected players
            for local_idx in local_indices:
                selected_data['ca'].append(batch_data['ca'][local_idx])
                selected_data['pa'].append(batch_data['pa'][local_idx])
                selected_data['country_idx'].append(batch_data['country_idx'][local_idx])
                selected_data['age'].append(batch_data['age'][local_idx])
                selected_data['height'].append(batch_data['height'][local_idx])
                selected_data['weight'].append(batch_data['weight'][local_idx])
        
        # Convert to numpy arrays
        for key in selected_data:
            selected_data[key] = np.array(selected_data[key])
        
        # Generate names
        print("   Generating names...")
        full_names = self.generate_names(
            selected_data['country_idx'],
            len(selected_data['ca'])
        )
        
        elapsed = time.time() - start_time
        
        stats = {
            'total_generated': self.total_players,
            'selected': len(selected_data['ca']),
            'ca_mean': float(np.mean(selected_data['ca'])),
            'ca_min': int(np.min(selected_data['ca'])),
            'ca_max': int(np.max(selected_data['ca'])),
            'pa_mean': float(np.mean(selected_data['pa'])),
            'pa_min': int(np.min(selected_data['pa'])),
            'pa_max': int(np.max(selected_data['pa'])),
            'time_seconds': elapsed,
            'speed': self.total_players / elapsed,
        }
        
        print(f"\n✅ PASS 2 Complete")
        print(f"   Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"   Generation speed: {stats['speed']:,.0f} players/sec")
        
        return selected_data, stats
    
    def visualize_distribution(self, selected_data: Dict[str, np.ndarray]):
        """Draw CLI charts comparing ALL vs SELECTED players."""
        print("\n" + "="*70)
        print("📊 PLAYER ABILITY DISTRIBUTION")
        print("   (Red=ALL generated players, Green=SELECTED top players)")
        print("="*70)
        
        # CA Distribution - Compare ALL vs SELECTED
        print("\n🎯 CA (Current Ability) Distribution:")
        print("   Range       | ALL Players          | SELECTED Players")
        print("   " + "-"*65)
        ca_ranges = [(20,30), (30,40), (40,50), (50,60), (60,70), (70,80), (80,90), (90,100), (100,110)]
        for min_ca, max_ca in ca_ranges:
            all_count = np.sum(self.all_ca_hist[min_ca:max_ca])
            selected_mask = (selected_data['ca'] >= min_ca) & (selected_data['ca'] < max_ca)
            selected_count = np.sum(selected_mask)
            
            all_pct = all_count / self.total_players * 100
            selected_pct = selected_count / len(selected_data['ca']) * 100 if len(selected_data['ca']) > 0 else 0
            
            bar_all = "█" * int(all_pct / 2)
            bar_selected = "▓" * int(selected_pct / 2)
            
            print(f"   {min_ca:3d}-{max_ca:3d} | {bar_all:20s} {all_count:8,} ({all_pct:4.1f}%) | {bar_selected:10s} {selected_count:5,} ({selected_pct:4.1f}%)")
        
        # PA Distribution - Compare ALL vs SELECTED
        print("\n⭐ PA (Potential Ability) Distribution:")
        print("   Range       | ALL Players          | SELECTED Players")
        print("   " + "-"*65)
        pa_ranges = [(30,60), (60,90), (90,120), (120,150), (150,180), (180,201)]
        for min_pa, max_pa in pa_ranges:
            all_count = np.sum(self.all_pa_hist[min_pa:max_pa])
            selected_mask = (selected_data['pa'] >= min_pa) & (selected_data['pa'] < max_pa)
            selected_count = np.sum(selected_mask)
            
            all_pct = all_count / self.total_players * 100
            selected_pct = selected_count / len(selected_data['pa']) * 100 if len(selected_data['pa']) > 0 else 0
            
            bar_all = "█" * int(all_pct / 2)
            bar_selected = "▓" * int(selected_pct / 2)
            
            print(f"   {min_pa:3d}-{max_pa:3d} | {bar_all:20s} {all_count:8,} ({all_pct:4.1f}%) | {bar_selected:10s} {selected_count:5,} ({selected_pct:4.1f}%)")
        
        # Country Distribution - ALL players
        print("\n🌍 Country Distribution (ALL Players):")
        countries = ['ENG', 'ESP', 'GER', 'ITA', 'FRA', 'BRA', 'ARG', 'POR', 'NED', 'BEL', 
                     'CHN', 'JPN', 'KOR', 'USA', 'MEX']
        total_all = np.sum(self.all_country_hist)
        sorted_idx = np.argsort(-self.all_country_hist)[:10]
        max_count = self.all_country_hist[sorted_idx[0]]
        
        for idx in sorted_idx:
            country = countries[idx] if idx < len(countries) else f"IDX_{idx}"
            count = self.all_country_hist[idx]
            pct = count / total_all * 100
            bar = "█" * int((count / max_count) * 30)
            print(f"   {country:4s} | {bar} {count:,} ({pct:4.1f}%)")
        
        # Age Distribution for SELECTED players
        print("\n🎂 Age Distribution (SELECTED Players):")
        unique, counts = np.unique(selected_data['age'], return_counts=True)
        max_count = max(counts) if len(counts) > 0 else 1
        for age, count in zip(unique, counts):
            pct = count / len(selected_data['age']) * 100
            bar = "▓" * int((count / max_count) * 35)
            print(f"   Age {age:2d} | {bar} {count:,} ({pct:4.1f}%)")
        
        print("="*70)
    
    def _draw_histogram(self, values: np.ndarray, bins: List[int], min_val: int, max_val: int, label: str):
        """Draw ASCII histogram."""
        counts, _ = np.histogram(values, bins=[min_val] + bins + [max_val + 1])
        max_count = max(counts) if max(counts) > 0 else 1
        width = 40
        
        for i, (bin_val, count) in enumerate(zip([min_val] + bins, counts)):
            bar_length = int((count / max_count) * width)
            bar = "█" * bar_length
            percentage = count / len(values) * 100
            range_str = f"{bin_val:3d}-{bins[i] if i < len(bins) else max_val:3d}"
            print(f"   {range_str} | {bar} {count:,} ({percentage:4.1f}%)")
    
    def _draw_country_chart(self, country_indices: np.ndarray):
        """Draw country distribution chart."""
        countries = ['ENG', 'ESP', 'GER', 'ITA', 'FRA', 'BRA', 'ARG', 'POR', 'NED', 'BEL', 
                     'CHN', 'JPN', 'KOR', 'USA', 'MEX']
        unique, counts = np.unique(country_indices, return_counts=True)
        sorted_idx = np.argsort(-counts)[:10]
        max_count = counts[sorted_idx[0]] if len(counts) > 0 else 1
        width = 30
        
        for idx in sorted_idx:
            country = countries[unique[idx]] if unique[idx] < len(countries) else f"IDX_{unique[idx]}"
            count = counts[idx]
            bar_length = int((count / max_count) * width)
            bar = "█" * bar_length
            percentage = count / len(country_indices) * 100
            print(f"   {country:4s} | {bar} {count:,} ({percentage:4.1f}%)")
    
    def _draw_age_chart(self, ages: np.ndarray):
        """Draw age distribution chart."""
        unique, counts = np.unique(ages, return_counts=True)
        max_count = max(counts) if len(counts) > 0 else 1
        width = 35
        
        for age, count in zip(unique, counts):
            bar_length = int((count / max_count) * width)
            bar = "█" * bar_length
            percentage = count / len(ages) * 100
            print(f"   Age {age:2d} | {bar} {count:,} ({percentage:4.1f}%)")

    def save_results(self, data: Dict[str, np.ndarray], stats: Dict, output_dir: str = "data/massive_players"):
        """Save results to binary format for efficiency."""
        import os
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"\n💾 Saving results to {output_dir}...")
        
        # Save as numpy binary format
        np.savez_compressed(
            f"{output_dir}/top_players.npz",
            ca=data['ca'],
            pa=data['pa'],
            country_idx=data['country_idx'],
            age=data['age'],
            height=data['height'],
            weight=data['weight'],
        )
        
        # Save stats
        import json
        with open(f"{output_dir}/stats.json", 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"✅ Saved {len(data['ca']):,} players to {output_dir}/top_players.npz")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate massive player dataset")
    parser.add_argument("--total", type=int, default=100_000_000, help="Total players to generate")
    parser.add_argument("--top-percent", type=float, default=0.1, help="Top percentage to keep")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="data/massive_players", help="Output directory")
    
    args = parser.parse_args()
    
    # Create generator
    generator = MassivePlayerGenerator(
        total_players=args.total,
        top_percent=args.top_percent,
        seed=args.seed,
    )
    
    # Run generation
    selected_data, stats = generator.run_two_pass_generation()
    
    # Display final statistics
    print("\n" + "=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)
    print(f"Total Generated: {stats['total_generated']:,}")
    print(f"Selected: {stats['selected']:,} ({stats['selected']/stats['total_generated']*100:.3f}%)")
    print(f"\nCA Statistics:")
    print(f"  Mean: {stats['ca_mean']:.1f}")
    print(f"  Range: {stats['ca_min']} - {stats['ca_max']}")
    print(f"\nPA Statistics:")
    print(f"  Mean: {stats['pa_mean']:.1f}")
    print(f"  Range: {stats['pa_min']} - {stats['pa_max']}")
    print(f"\nPerformance:")
    print(f"  Time: {stats['time_seconds']:.1f} seconds")
    print(f"  Speed: {stats['speed']:,.0f} players/second")
    print("=" * 80)
    
    # Visualize distribution
    generator.visualize_distribution(selected_data)
    
    # Save results
    generator.save_results(selected_data, stats, args.output)


if __name__ == "__main__":
    main()
