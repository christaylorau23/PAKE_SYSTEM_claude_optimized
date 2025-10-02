#!/bin/bash
# PAKE System - Memray Memory Profiler
# Phase 5: Performance Under Pressure - Advanced Memory Profiling
#
# Memray is a powerful memory profiler that can generate flame graphs
# and detailed memory allocation reports.
#
# Usage:
#   ./scripts/memray_profiler.sh run        # Run application with memray
#   ./scripts/memray_profiler.sh flamegraph # Generate flame graph from output
#   ./scripts/memray_profiler.sh stats      # Show memory statistics

set -e

MEMRAY_OUTPUT="memray_output.bin"
FLAMEGRAPH_OUTPUT="memray_flamegraph.html"
STATS_OUTPUT="memray_stats.txt"

function run_with_memray() {
    echo "🔥 Running application with Memray profiler..."
    echo "   Output: $MEMRAY_OUTPUT"
    echo ""

    # Run the application with memray
    poetry run memray run -o "$MEMRAY_OUTPUT" \
        python -m uvicorn src.pake_system.auth.example_app:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1

    echo ""
    echo "✅ Memray profiling complete"
    echo "   Output saved to: $MEMRAY_OUTPUT"
}

function generate_flamegraph() {
    if [ ! -f "$MEMRAY_OUTPUT" ]; then
        echo "❌ Error: Memray output file not found: $MEMRAY_OUTPUT"
        echo "   Run './scripts/memray_profiler.sh run' first"
        exit 1
    fi

    echo "🔥 Generating flame graph..."
    echo "   Input: $MEMRAY_OUTPUT"
    echo "   Output: $FLAMEGRAPH_OUTPUT"
    echo ""

    poetry run memray flamegraph "$MEMRAY_OUTPUT" -o "$FLAMEGRAPH_OUTPUT"

    echo ""
    echo "✅ Flame graph generated: $FLAMEGRAPH_OUTPUT"
    echo "   Open in browser to visualize memory usage"
}

function show_stats() {
    if [ ! -f "$MEMRAY_OUTPUT" ]; then
        echo "❌ Error: Memray output file not found: $MEMRAY_OUTPUT"
        echo "   Run './scripts/memray_profiler.sh run' first"
        exit 1
    fi

    echo "📊 Memory Statistics"
    echo "=" * 80
    echo ""

    poetry run memray stats "$MEMRAY_OUTPUT" | tee "$STATS_OUTPUT"

    echo ""
    echo "✅ Statistics saved to: $STATS_OUTPUT"
}

function show_tree() {
    if [ ! -f "$MEMRAY_OUTPUT" ]; then
        echo "❌ Error: Memray output file not found: $MEMRAY_OUTPUT"
        echo "   Run './scripts/memray_profiler.sh run' first"
        exit 1
    fi

    echo "🌳 Memory Allocation Tree"
    echo "=" * 80
    echo ""

    poetry run memray tree "$MEMRAY_OUTPUT"
}

function show_help() {
    echo "PAKE System - Memray Memory Profiler"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  run         Run application with memray profiler"
    echo "  flamegraph  Generate flame graph visualization"
    echo "  stats       Show memory statistics"
    echo "  tree        Show memory allocation tree"
    echo "  clean       Remove profiling output files"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 run"
    echo "  $0 flamegraph"
    echo "  $0 stats"
}

function clean_output() {
    echo "🧹 Cleaning memray output files..."

    rm -f "$MEMRAY_OUTPUT" "$FLAMEGRAPH_OUTPUT" "$STATS_OUTPUT"

    echo "✅ Cleanup complete"
}

# Main command dispatcher
case "${1:-help}" in
    run)
        run_with_memray
        ;;
    flamegraph)
        generate_flamegraph
        ;;
    stats)
        show_stats
        ;;
    tree)
        show_tree
        ;;
    clean)
        clean_output
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
