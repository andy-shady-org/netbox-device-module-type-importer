#!/usr/bin/env python
"""
Benchmark script to compare synchronous vs async performance.
"""

import os
import sys
import time

# Add the module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities import GitHubGQLAPI
from utilities import GitHubGQLAPIAsync

# You'll need to set your GitHub token
token = os.environ.get("GITHUB_TOKEN")

if not token:
    print("Please set GITHUB_TOKEN environment variable")
    print("Example: export GITHUB_TOKEN=your_token_here")
    sys.exit(1)


def benchmark_sync(batch_size=50):
    """Benchmark synchronous version."""
    print("\n" + "=" * 60)
    print("SYNCHRONOUS VERSION")
    print("=" * 60)

    api = GitHubGQLAPI(token=token, owner="netbox-community", repo="devicetype-library")

    start_time = time.time()
    tree = api.get_tree(batch_size=batch_size, delay_between_batches=0)
    elapsed = time.time() - start_time

    total_vendors = len(tree)
    total_files = sum(len(files) for files in tree.values())

    print(f"\nResults:")
    print(f"  Time: {elapsed:.2f} seconds")
    print(f"  Vendors: {total_vendors}")
    print(f"  Files: {total_files}")
    print(f"  Speed: {total_files/elapsed:.1f} files/second")

    return {
        "name": "Synchronous",
        "elapsed": elapsed,
        "vendors": total_vendors,
        "files": total_files,
        "fps": total_files / elapsed,
    }


def benchmark_async(
    batch_size=50, max_concurrent_requests=10, max_concurrent_vendors=5
):
    """Benchmark async version."""
    print("\n" + "=" * 60)
    print("ASYNC VERSION")
    print(
        f"Settings: max_concurrent_requests={max_concurrent_requests}, max_concurrent_vendors={max_concurrent_vendors}"
    )
    print("=" * 60)

    api = GitHubGQLAPIAsync(
        token=token, owner="netbox-community", repo="devicetype-library"
    )

    start_time = time.time()
    tree = api.get_tree(
        batch_size=batch_size,
        max_concurrent_requests=max_concurrent_requests,
        max_concurrent_vendors=max_concurrent_vendors,
    )
    elapsed = time.time() - start_time

    total_vendors = len(tree)
    total_files = sum(len(files) for files in tree.values())

    print(f"\nResults:")
    print(f"  Time: {elapsed:.2f} seconds")
    print(f"  Vendors: {total_vendors}")
    print(f"  Files: {total_files}")
    print(f"  Speed: {total_files/elapsed:.1f} files/second")

    return {
        "name": f"Async (req={max_concurrent_requests}, vendors={max_concurrent_vendors})",
        "elapsed": elapsed,
        "vendors": total_vendors,
        "files": total_files,
        "fps": total_files / elapsed,
    }


def main():
    print("GitHub Device Type Import - Sync vs Async Benchmark")
    print("=" * 60)

    print("\nNote: This will make many API requests. Make sure you have")
    print("sufficient API rate limit remaining!")

    choice = input("\nRun benchmark? (y/N): ").strip().lower()
    if choice != "y":
        print("Aborted.")
        return

    results = []

    # Benchmark synchronous version
    print("\n" + "#" * 60)
    print("# Test 1: Synchronous (Current Implementation)")
    print("#" * 60)
    sync_result = benchmark_sync(batch_size=50)
    results.append(sync_result)

    print("\nWaiting 5 seconds before next test...")
    time.sleep(5)

    # Benchmark async with conservative settings
    print("\n" + "#" * 60)
    print("# Test 2: Async - Conservative (5 concurrent vendors)")
    print("#" * 60)
    async_conservative = benchmark_async(
        batch_size=50,
        max_concurrent_requests=10,
        max_concurrent_vendors=5,
    )
    results.append(async_conservative)

    print("\nWaiting 5 seconds before next test...")
    time.sleep(5)

    # Benchmark async with moderate settings
    print("\n" + "#" * 60)
    print("# Test 3: Async - Moderate (10 concurrent vendors)")
    print("#" * 60)
    async_moderate = benchmark_async(
        batch_size=50,
        max_concurrent_requests=15,
        max_concurrent_vendors=10,
    )
    results.append(async_moderate)

    print("\nWaiting 5 seconds before next test...")
    time.sleep(5)

    # Benchmark async with aggressive settings
    print("\n" + "#" * 60)
    print("# Test 4: Async - Aggressive (20 concurrent vendors)")
    print("#" * 60)
    async_aggressive = benchmark_async(
        batch_size=50,
        max_concurrent_requests=20,
        max_concurrent_vendors=20,
    )
    results.append(async_aggressive)

    # Print comparison
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    print(f"{'Configuration':<40} {'Time (s)':<12} {'Files/s':<12} {'Speedup':<10}")
    print("-" * 80)

    baseline = sync_result["elapsed"]
    for result in results:
        speedup = baseline / result["elapsed"] if result["elapsed"] > 0 else 1
        print(
            f"{result['name']:<40} {result['elapsed']:>10.2f}s {result['fps']:>10.1f}  {speedup:>8.2f}×"
        )

    print("=" * 80)

    # Calculate improvement
    best_async = min(
        [r for r in results if "Async" in r["name"]], key=lambda x: x["elapsed"]
    )
    improvement = baseline / best_async["elapsed"]
    time_saved = baseline - best_async["elapsed"]

    print(f"\n🚀 BEST ASYNC SPEEDUP: {improvement:.1f}× faster than synchronous!")
    print(f"⏱️  TIME SAVED: {time_saved:.1f} seconds ({time_saved/60:.1f} minutes)")

    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    if improvement >= 4:
        print("✅ Async provides EXCELLENT speedup (4×+)")
        print("   Recommendation: Use async version for production!")
    elif improvement >= 2.5:
        print("✅ Async provides GREAT speedup (2.5-4×)")
        print("   Recommendation: Use async version for most use cases")
    elif improvement >= 1.5:
        print("✅ Async provides GOOD speedup (1.5-2.5×)")
        print("   Recommendation: Use async if time is critical")
    else:
        print("⚠️  Async provides MINIMAL speedup (<1.5×)")
        print("   Recommendation: Sync version is simpler, stick with it")

    print("\nOptimal Settings:")
    print(
        f"  max_concurrent_vendors: {best_async['name'].split('vendors=')[1].split(')')[0]}"
    )
    print(f"  batch_size: 50")
    print(
        f"  Expected time: {best_async['elapsed']:.1f}s ({best_async['elapsed']/60:.1f} minutes)"
    )


if __name__ == "__main__":
    main()
