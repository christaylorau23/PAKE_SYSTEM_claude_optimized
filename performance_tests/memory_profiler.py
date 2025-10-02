"""
Memory Leak Detection and Profiling
===================================

This module provides comprehensive memory leak detection and profiling
for the PAKE System using Python's built-in tracemalloc and Memray.

Key Features:
- Memory allocation tracking with tracemalloc
- Advanced memory profiling with Memray
- Memory leak detection and analysis
- Memory usage trend monitoring
- Automated memory optimization recommendations
"""

import tracemalloc
import gc
import psutil
import time
import json
import os
import sys
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
import threading
import subprocess
import tempfile


@dataclass
class MemorySnapshot:
    """Memory snapshot data structure"""
    timestamp: str
    total_memory_mb: float
    available_memory_mb: float
    memory_usage_percent: float
    python_memory_mb: float
    tracemalloc_current_mb: float
    tracemalloc_peak_mb: float
    gc_counts: Dict[str, int]
    top_allocations: List[Dict[str, Any]]


@dataclass
class MemoryLeakPattern:
    """Memory leak pattern detection"""
    pattern_id: str
    leak_type: str
    description: str
    severity: str
    memory_growth_mb: float
    growth_rate_mb_per_hour: float
    affected_objects: List[str]
    suggested_fix: str


class MemoryProfiler:
    """Comprehensive memory profiler using tracemalloc"""
    
    def __init__(self, log_file: str = "logs/memory_profiling.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Memory tracking
        self.snapshots: List[MemorySnapshot] = []
        self.leak_patterns: List[MemoryLeakPattern] = []
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Configuration
        self.snapshot_interval_seconds = 30
        self.memory_growth_threshold_mb = 10.0  # 10MB growth threshold
        self.leak_detection_window_hours = 1.0  # 1 hour window
        
        # Initialize tracemalloc
        self._initialize_tracemalloc()
    
    def _initialize_tracemalloc(self):
        """Initialize tracemalloc for memory tracking"""
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            print("Tracemalloc started - memory tracking enabled")
    
    def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous memory monitoring"""
        if self.monitoring_active:
            print("Memory monitoring already active")
            return
        
        self.snapshot_interval_seconds = interval_seconds
        self.monitoring_active = True
        
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        
        print(f"Memory monitoring started (interval: {interval_seconds}s)")
    
    def stop_monitoring(self):
        """Stop continuous memory monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("Memory monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                self.take_snapshot()
                self._detect_memory_leaks()
                time.sleep(self.snapshot_interval_seconds)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(5)
    
    def take_snapshot(self) -> MemorySnapshot:
        """Take a memory snapshot"""
        # System memory info
        memory_info = psutil.virtual_memory()
        
        # Python process memory
        process = psutil.Process()
        python_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Tracemalloc info
        tracemalloc_current = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        tracemalloc_peak = tracemalloc.get_traced_memory()[1] / 1024 / 1024  # MB
        
        # Garbage collector info
        gc_counts = {
            "generation_0": gc.get_count()[0],
            "generation_1": gc.get_count()[1],
            "generation_2": gc.get_count()[2]
        }
        
        # Top memory allocations
        top_allocations = self._get_top_allocations()
        
        snapshot = MemorySnapshot(
            timestamp=datetime.now().isoformat(),
            total_memory_mb=memory_info.total / 1024 / 1024,
            available_memory_mb=memory_info.available / 1024 / 1024,
            memory_usage_percent=memory_info.percent,
            python_memory_mb=python_memory,
            tracemalloc_current_mb=tracemalloc_current,
            tracemalloc_peak_mb=tracemalloc_peak,
            gc_counts=gc_counts,
            top_allocations=top_allocations
        )
        
        self.snapshots.append(snapshot)
        
        # Keep only recent snapshots (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.snapshots = [
            s for s in self.snapshots 
            if datetime.fromisoformat(s.timestamp) > cutoff_time
        ]
        
        return snapshot
    
    def _get_top_allocations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top memory allocations"""
        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            allocations = []
            for stat in top_stats[:limit]:
                allocations.append({
                    "filename": stat.traceback.format()[0] if stat.traceback else "unknown",
                    "size_mb": stat.size / 1024 / 1024,
                    "count": stat.count
                })
            
            return allocations
        except Exception as e:
            print(f"Error getting top allocations: {e}")
            return []
    
    def _detect_memory_leaks(self):
        """Detect memory leak patterns"""
        if len(self.snapshots) < 10:  # Need at least 10 snapshots
            return
        
        # Analyze memory growth trends
        recent_snapshots = self.snapshots[-10:]  # Last 10 snapshots
        
        # Calculate memory growth
        memory_growth = self._calculate_memory_growth(recent_snapshots)
        
        if memory_growth > self.memory_growth_threshold_mb:
            self._create_memory_leak_pattern(recent_snapshots, memory_growth)
    
    def _calculate_memory_growth(self, snapshots: List[MemorySnapshot]) -> float:
        """Calculate memory growth over time"""
        if len(snapshots) < 2:
            return 0.0
        
        start_memory = snapshots[0].python_memory_mb
        end_memory = snapshots[-1].python_memory_mb
        
        return end_memory - start_memory
    
    def _create_memory_leak_pattern(self, snapshots: List[MemorySnapshot], growth_mb: float):
        """Create memory leak pattern record"""
        pattern_id = f"memory_leak_{int(time.time())}"
        
        # Calculate growth rate
        time_span_hours = len(snapshots) * self.snapshot_interval_seconds / 3600
        growth_rate = growth_mb / time_span_hours if time_span_hours > 0 else 0
        
        # Determine severity
        if growth_rate > 50:  # 50MB/hour
            severity = "critical"
        elif growth_rate > 20:  # 20MB/hour
            severity = "high"
        elif growth_rate > 10:  # 10MB/hour
            severity = "medium"
        else:
            severity = "low"
        
        # Analyze top allocations for leak sources
        affected_objects = self._analyze_leak_sources(snapshots)
        
        # Generate suggested fix
        suggested_fix = self._generate_memory_fix_suggestion(affected_objects, growth_rate)
        
        leak_pattern = MemoryLeakPattern(
            pattern_id=pattern_id,
            leak_type="memory_growth",
            description=f"Memory growth of {growth_mb:.2f}MB detected",
            severity=severity,
            memory_growth_mb=growth_mb,
            growth_rate_mb_per_hour=growth_rate,
            affected_objects=affected_objects,
            suggested_fix=suggested_fix
        )
        
        self.leak_patterns.append(leak_pattern)
        
        print(f"Memory leak detected: {growth_mb:.2f}MB growth, {growth_rate:.2f}MB/hour")
    
    def _analyze_leak_sources(self, snapshots: List[MemorySnapshot]) -> List[str]:
        """Analyze potential leak sources"""
        sources = []
        
        # Check for increasing allocation counts
        for snapshot in snapshots:
            for allocation in snapshot.top_allocations:
                if allocation["count"] > 1000:  # High allocation count
                    sources.append(allocation["filename"])
        
        # Check garbage collector behavior
        gc_counts = [s.gc_counts for s in snapshots]
        if len(gc_counts) > 1:
            if gc_counts[-1]["generation_2"] > gc_counts[0]["generation_2"] * 2:
                sources.append("garbage_collection_ineffective")
        
        return list(set(sources))  # Remove duplicates
    
    def _generate_memory_fix_suggestion(self, affected_objects: List[str], growth_rate: float) -> str:
        """Generate memory fix suggestions"""
        suggestions = []
        
        if "garbage_collection_ineffective" in affected_objects:
            suggestions.append("Force garbage collection with gc.collect()")
            suggestions.append("Review object lifecycle management")
        
        if any("cache" in obj.lower() for obj in affected_objects):
            suggestions.append("Implement cache size limits and TTL")
            suggestions.append("Review cache eviction policies")
        
        if any("database" in obj.lower() for obj in affected_objects):
            suggestions.append("Close database connections properly")
            suggestions.append("Use connection pooling")
        
        if any("file" in obj.lower() for obj in affected_objects):
            suggestions.append("Ensure file handles are closed")
            suggestions.append("Use context managers for file operations")
        
        if growth_rate > 20:
            suggestions.append("Consider implementing memory monitoring alerts")
            suggestions.append("Review for circular references")
        
        return "; ".join(suggestions) if suggestions else "Review memory usage patterns"
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get comprehensive memory summary"""
        if not self.snapshots:
            return {"message": "No memory snapshots available"}
        
        latest_snapshot = self.snapshots[-1]
        
        # Calculate trends
        memory_trend = self._calculate_memory_trend()
        
        # Memory leak summary
        leak_summary = {
            "total_leaks_detected": len(self.leak_patterns),
            "critical_leaks": len([l for l in self.leak_patterns if l.severity == "critical"]),
            "high_leaks": len([l for l in self.leak_patterns if l.severity == "high"]),
            "medium_leaks": len([l for l in self.leak_patterns if l.severity == "medium"]),
            "low_leaks": len([l for l in self.leak_patterns if l.severity == "low"])
        }
        
        return {
            "current_memory": {
                "python_memory_mb": latest_snapshot.python_memory_mb,
                "tracemalloc_current_mb": latest_snapshot.tracemalloc_current_mb,
                "tracemalloc_peak_mb": latest_snapshot.tracemalloc_peak_mb,
                "system_memory_percent": latest_snapshot.memory_usage_percent
            },
            "memory_trend": memory_trend,
            "leak_summary": leak_summary,
            "top_allocations": latest_snapshot.top_allocations[:5],
            "gc_counts": latest_snapshot.gc_counts
        }
    
    def _calculate_memory_trend(self) -> Dict[str, Any]:
        """Calculate memory usage trend"""
        if len(self.snapshots) < 2:
            return {"trend": "insufficient_data"}
        
        recent_snapshots = self.snapshots[-10:] if len(self.snapshots) >= 10 else self.snapshots
        
        memory_values = [s.python_memory_mb for s in recent_snapshots]
        
        # Simple trend calculation
        if len(memory_values) >= 2:
            start_memory = memory_values[0]
            end_memory = memory_values[-1]
            growth = end_memory - start_memory
            
            if growth > 10:
                trend = "increasing"
            elif growth < -10:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "growth_mb": growth if len(memory_values) >= 2 else 0,
            "snapshots_analyzed": len(recent_snapshots)
        }
    
    def generate_memory_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory report"""
        summary = self.get_memory_summary()
        
        recommendations = []
        
        # Memory leak recommendations
        if summary["leak_summary"]["total_leaks_detected"] > 0:
            recommendations.append({
                "priority": "high",
                "category": "Memory Leaks",
                "description": f"Detected {summary['leak_summary']['total_leaks_detected']} memory leak patterns",
                "impact": "Memory usage growth over time",
                "suggestions": [
                    "Review object lifecycle management",
                    "Implement proper resource cleanup",
                    "Use context managers for resource management",
                    "Monitor memory usage in production"
                ]
            })
        
        # High memory usage recommendations
        if summary["current_memory"]["python_memory_mb"] > 500:  # 500MB
            recommendations.append({
                "priority": "medium",
                "category": "High Memory Usage",
                "description": "Python process using significant memory",
                "impact": "System performance degradation",
                "suggestions": [
                    "Implement memory-efficient data structures",
                    "Use generators instead of lists where possible",
                    "Consider memory-mapped files for large datasets",
                    "Implement memory usage monitoring"
                ]
            })
        
        # Garbage collection recommendations
        gc_counts = summary["gc_counts"]
        if gc_counts["generation_2"] > 1000:
            recommendations.append({
                "priority": "low",
                "category": "Garbage Collection",
                "description": "High number of long-lived objects",
                "impact": "Memory fragmentation",
                "suggestions": [
                    "Review object retention patterns",
                    "Consider implementing object pooling",
                    "Use weak references where appropriate",
                    "Monitor garbage collection performance"
                ]
            })
        
        return {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_snapshots": len(self.snapshots),
                "monitoring_duration_hours": len(self.snapshots) * self.snapshot_interval_seconds / 3600
            },
            "memory_summary": summary,
            "recommendations": recommendations,
            "optimization_priority": self._calculate_memory_optimization_priority(recommendations)
        }
    
    def _calculate_memory_optimization_priority(self, recommendations: List[Dict]) -> str:
        """Calculate memory optimization priority"""
        if not recommendations:
            return "low"
        
        priorities = [r["priority"] for r in recommendations]
        if "high" in priorities:
            return "high"
        elif "medium" in priorities:
            return "medium"
        else:
            return "low"
    
    def save_report(self, filename: str = None) -> Path:
        """Save memory report to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"memory_profiling_report_{timestamp}.json"
        
        report = self.generate_memory_report()
        
        report_file = Path("performance_tests/results") / filename
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Memory profiling report saved to: {report_file}")
        return report_file


class MemrayProfiler:
    """Advanced memory profiler using Memray"""
    
    def __init__(self):
        self.memray_available = self._check_memray_availability()
    
    def _check_memray_availability(self) -> bool:
        """Check if Memray is available"""
        try:
            import memray
            return True
        except ImportError:
            print("Memray not available - install with: pip install memray")
            return False
    
    def start_profiling(self, output_file: str = None) -> str:
        """Start Memray profiling"""
        if not self.memray_available:
            raise RuntimeError("Memray not available")
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"performance_tests/results/memray_profile_{timestamp}.bin"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Start profiling
        import memray
        memray.start_tracing(str(output_path))
        
        print(f"Memray profiling started - output: {output_path}")
        return str(output_path)
    
    def stop_profiling(self):
        """Stop Memray profiling"""
        if not self.memray_available:
            return
        
        import memray
        memray.stop_tracing()
        print("Memray profiling stopped")
    
    def generate_flame_graph(self, profile_file: str, output_file: str = None):
        """Generate flame graph from Memray profile"""
        if not self.memray_available:
            raise RuntimeError("Memray not available")
        
        if not output_file:
            output_file = profile_file.replace('.bin', '_flamegraph.html')
        
        try:
            # Generate flame graph
            subprocess.run([
                "memray", "flamegraph",
                profile_file,
                "--output", output_file
            ], check=True)
            
            print(f"Flame graph generated: {output_file}")
            return output_file
            
        except subprocess.CalledProcessError as e:
            print(f"Error generating flame graph: {e}")
            return None
    
    def generate_memory_stats(self, profile_file: str) -> Dict[str, Any]:
        """Generate memory statistics from Memray profile"""
        if not self.memray_available:
            raise RuntimeError("Memray not available")
        
        try:
            # Generate stats
            result = subprocess.run([
                "memray", "stats",
                profile_file,
                "--json"
            ], capture_output=True, text=True, check=True)
            
            return json.loads(result.stdout)
            
        except subprocess.CalledProcessError as e:
            print(f"Error generating memory stats: {e}")
            return {}


def main():
    """Main function for memory profiling"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PAKE System Memory Profiler")
    parser.add_argument("--start-monitoring", action="store_true",
                       help="Start continuous memory monitoring")
    parser.add_argument("--stop-monitoring", action="store_true",
                       help="Stop continuous memory monitoring")
    parser.add_argument("--take-snapshot", action="store_true",
                       help="Take a memory snapshot")
    parser.add_argument("--generate-report", action="store_true",
                       help="Generate memory report")
    parser.add_argument("--interval", type=int, default=30,
                       help="Monitoring interval in seconds")
    parser.add_argument("--memray-profile", action="store_true",
                       help="Start Memray profiling")
    parser.add_argument("--memray-stop", action="store_true",
                       help="Stop Memray profiling")
    
    args = parser.parse_args()
    
    # Initialize profiler
    profiler = MemoryProfiler()
    memray_profiler = MemrayProfiler()
    
    try:
        if args.start_monitoring:
            profiler.start_monitoring(args.interval)
            print("Memory monitoring started. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                profiler.stop_monitoring()
        
        elif args.stop_monitoring:
            profiler.stop_monitoring()
        
        elif args.take_snapshot:
            snapshot = profiler.take_snapshot()
            print(f"Memory snapshot taken: {snapshot.python_memory_mb:.2f}MB")
        
        elif args.generate_report:
            report_file = profiler.save_report()
            print(f"Memory report generated: {report_file}")
            
            # Print summary
            summary = profiler.get_memory_summary()
            print("\n" + "="*60)
            print("MEMORY PROFILING SUMMARY")
            print("="*60)
            print(f"Python Memory: {summary['current_memory']['python_memory_mb']:.2f}MB")
            print(f"Tracemalloc Current: {summary['current_memory']['tracemalloc_current_mb']:.2f}MB")
            print(f"Tracemalloc Peak: {summary['current_memory']['tracemalloc_peak_mb']:.2f}MB")
            print(f"Memory Trend: {summary['memory_trend']['trend']}")
            print(f"Leaks Detected: {summary['leak_summary']['total_leaks_detected']}")
        
        elif args.memray_profile:
            profile_file = memray_profiler.start_profiling()
            print(f"Memray profiling started: {profile_file}")
        
        elif args.memray_stop:
            memray_profiler.stop_profiling()
    
    except KeyboardInterrupt:
        print("\nProfiling interrupted by user")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
