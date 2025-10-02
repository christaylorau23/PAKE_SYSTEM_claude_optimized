#!/usr/bin/env python3
"""
PAKE System - Memory Profiling Utility
Phase 5: Performance Under Pressure - Memory Leak Detection

This script uses Python's built-in tracemalloc module to profile memory usage
and detect potential memory leaks.

Usage:
    # Profile a specific function
    python scripts/memory_profiler.py --function test_endpoint

    # Profile the application during a test run
    python scripts/memory_profiler.py --duration 300

    # Compare memory snapshots
    python scripts/memory_profiler.py --compare snapshot1.pkl snapshot2.pkl
"""

import argparse
import asyncio
import gc
import json
import linecache
import pickle
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

import psutil


class MemoryProfiler:
    """Memory profiling and leak detection utility"""

    def __init__(self, top_stats: int = 10):
        """
        Initialize memory profiler.

        Args:
            top_stats: Number of top memory consumers to display
        """
        self.top_stats = top_stats
        self.snapshots: List[Tuple[str, tracemalloc.Snapshot]] = []
        self.process = psutil.Process()

    def start(self):
        """Start memory profiling"""
        tracemalloc.start()
        print(f"🔍 Memory profiling started at {datetime.now()}")
        print(f"Initial memory usage: {self._get_memory_mb():.2f} MB\n")

    def stop(self):
        """Stop memory profiling"""
        tracemalloc.stop()
        print(f"\n✅ Memory profiling stopped at {datetime.now()}")

    def take_snapshot(self, label: str = "snapshot") -> tracemalloc.Snapshot:
        """
        Take a memory snapshot.

        Args:
            label: Label for this snapshot

        Returns:
            Memory snapshot
        """
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append((label, snapshot))
        print(f"📸 Snapshot '{label}' taken - Memory: {self._get_memory_mb():.2f} MB")
        return snapshot

    def display_top_stats(self, snapshot: tracemalloc.Snapshot = None):
        """
        Display top memory consumers.

        Args:
            snapshot: Snapshot to analyze (uses latest if not provided)
        """
        if snapshot is None:
            if not self.snapshots:
                snapshot = tracemalloc.take_snapshot()
            else:
                snapshot = self.snapshots[-1][1]

        print(f"\n📊 Top {self.top_stats} Memory Consumers")
        print("=" * 80)

        top_stats = snapshot.statistics("lineno")

        for index, stat in enumerate(top_stats[: self.top_stats], 1):
            frame = stat.traceback[0]
            print(f"\n#{index}: {frame.filename}:{frame.lineno}")
            print(f"    Size: {stat.size / 1024 / 1024:.2f} MB")
            print(f"    Count: {stat.count} blocks")

            # Display source code line
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                print(f"    Code: {line}")

    def compare_snapshots(
        self, snapshot1: tracemalloc.Snapshot, snapshot2: tracemalloc.Snapshot
    ) -> List[tracemalloc.StatisticDiff]:
        """
        Compare two memory snapshots to detect leaks.

        Args:
            snapshot1: Earlier snapshot
            snapshot2: Later snapshot

        Returns:
            List of memory differences
        """
        print(f"\n🔬 Comparing Memory Snapshots")
        print("=" * 80)

        differences = snapshot2.compare_to(snapshot1, "lineno")

        print(f"\nTop {self.top_stats} Memory Growth Areas:\n")

        for index, diff in enumerate(differences[: self.top_stats], 1):
            frame = diff.traceback[0]
            size_diff_mb = diff.size_diff / 1024 / 1024
            count_diff = diff.count_diff

            if diff.size_diff > 0:
                print(f"#{index}: {frame.filename}:{frame.lineno}")
                print(f"    Growth: +{size_diff_mb:.2f} MB ({count_diff:+d} blocks)")

                # Display source code line
                line = linecache.getline(frame.filename, frame.lineno).strip()
                if line:
                    print(f"    Code: {line}")
                print()

        return differences

    def detect_memory_leaks(
        self, threshold_mb: float = 10.0
    ) -> List[tracemalloc.StatisticDiff]:
        """
        Detect potential memory leaks by comparing first and last snapshots.

        Args:
            threshold_mb: Threshold in MB to consider as potential leak

        Returns:
            List of potential memory leaks
        """
        if len(self.snapshots) < 2:
            print("⚠️ Need at least 2 snapshots to detect leaks")
            return []

        first_snapshot = self.snapshots[0][1]
        last_snapshot = self.snapshots[-1][1]

        print(f"\n🚨 Memory Leak Detection")
        print("=" * 80)
        print(f"Comparing '{self.snapshots[0][0]}' to '{self.snapshots[-1][0]}'")

        differences = last_snapshot.compare_to(first_snapshot, "lineno")

        # Filter for significant memory growth
        potential_leaks = [
            diff
            for diff in differences
            if diff.size_diff / 1024 / 1024 > threshold_mb
        ]

        if not potential_leaks:
            print(f"✅ No significant memory leaks detected (threshold: {threshold_mb} MB)")
            return []

        print(f"\n⚠️ Found {len(potential_leaks)} potential memory leaks:\n")

        for index, diff in enumerate(potential_leaks, 1):
            frame = diff.traceback[0]
            size_diff_mb = diff.size_diff / 1024 / 1024

            print(f"#{index}: {frame.filename}:{frame.lineno}")
            print(f"    Leaked: +{size_diff_mb:.2f} MB")
            print(f"    Blocks: {diff.count_diff:+d}")

            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                print(f"    Code: {line}")
            print()

        return potential_leaks

    def _get_memory_mb(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024

    def save_snapshot(self, snapshot: tracemalloc.Snapshot, filename: str):
        """
        Save snapshot to file.

        Args:
            snapshot: Snapshot to save
            filename: Output filename
        """
        with open(filename, "wb") as f:
            pickle.dump(snapshot, f)
        print(f"💾 Snapshot saved to {filename}")

    def load_snapshot(self, filename: str) -> tracemalloc.Snapshot:
        """
        Load snapshot from file.

        Args:
            filename: Input filename

        Returns:
            Loaded snapshot
        """
        with open(filename, "rb") as f:
            snapshot = pickle.load(f)
        print(f"📂 Snapshot loaded from {filename}")
        return snapshot

    def generate_report(self, output_file: str = "memory_profile_report.json"):
        """
        Generate comprehensive memory profiling report.

        Args:
            output_file: Output JSON filename
        """
        if not self.snapshots:
            print("⚠️ No snapshots to report")
            return

        report = {
            "timestamp": datetime.now().isoformat(),
            "num_snapshots": len(self.snapshots),
            "snapshots": [],
            "memory_growth": [],
        }

        # Analyze each snapshot
        for label, snapshot in self.snapshots:
            stats = snapshot.statistics("lineno")
            total_size_mb = sum(stat.size for stat in stats) / 1024 / 1024

            report["snapshots"].append(
                {
                    "label": label,
                    "total_size_mb": total_size_mb,
                    "num_allocations": sum(stat.count for stat in stats),
                    "top_consumers": [
                        {
                            "file": stat.traceback[0].filename,
                            "line": stat.traceback[0].lineno,
                            "size_mb": stat.size / 1024 / 1024,
                            "count": stat.count,
                        }
                        for stat in stats[: self.top_stats]
                    ],
                }
            )

        # Calculate memory growth between snapshots
        if len(self.snapshots) >= 2:
            for i in range(len(self.snapshots) - 1):
                label1, snap1 = self.snapshots[i]
                label2, snap2 = self.snapshots[i + 1]

                differences = snap2.compare_to(snap1, "lineno")
                total_growth_mb = sum(diff.size_diff for diff in differences) / 1024 / 1024

                report["memory_growth"].append(
                    {
                        "from": label1,
                        "to": label2,
                        "growth_mb": total_growth_mb,
                        "top_growth_areas": [
                            {
                                "file": diff.traceback[0].filename,
                                "line": diff.traceback[0].lineno,
                                "growth_mb": diff.size_diff / 1024 / 1024,
                                "count_diff": diff.count_diff,
                            }
                            for diff in differences[: self.top_stats]
                            if diff.size_diff > 0
                        ],
                    }
                )

        # Save report
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Memory profiling report saved to {output_file}")


async def profile_application(duration: int = 60, interval: int = 10):
    """
    Profile application memory usage over time.

    Args:
        duration: Total profiling duration in seconds
        interval: Interval between snapshots in seconds
    """
    profiler = MemoryProfiler(top_stats=10)
    profiler.start()

    # Take initial snapshot
    profiler.take_snapshot("initial")

    # Take periodic snapshots
    num_intervals = duration // interval
    for i in range(1, num_intervals + 1):
        await asyncio.sleep(interval)
        gc.collect()  # Force garbage collection
        profiler.take_snapshot(f"interval_{i}")

    # Take final snapshot
    profiler.take_snapshot("final")

    # Display results
    profiler.display_top_stats()
    profiler.detect_memory_leaks(threshold_mb=5.0)

    # Generate report
    profiler.generate_report()

    profiler.stop()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PAKE System Memory Profiler"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Profiling duration in seconds (default: 60)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Snapshot interval in seconds (default: 10)",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("SNAPSHOT1", "SNAPSHOT2"),
        help="Compare two saved snapshots",
    )
    parser.add_argument(
        "--output",
        default="memory_profile_report.json",
        help="Output report filename",
    )

    args = parser.parse_args()

    if args.compare:
        # Compare two saved snapshots
        profiler = MemoryProfiler()
        snap1 = profiler.load_snapshot(args.compare[0])
        snap2 = profiler.load_snapshot(args.compare[1])
        profiler.compare_snapshots(snap1, snap2)
    else:
        # Profile application
        print(f"🚀 Starting memory profiler for {args.duration} seconds")
        print(f"   Snapshot interval: {args.interval} seconds\n")
        asyncio.run(profile_application(args.duration, args.interval))


if __name__ == "__main__":
    main()
