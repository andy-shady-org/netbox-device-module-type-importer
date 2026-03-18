#!/usr/bin/env python
"""
Benchmark script to compare performance with different settings.
"""

import os
import sys
import time

# Add the module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities import GitHubGQLAPI

# You'll need to set your GitHub token
token = os.environ.get("GITHUB_TOKEN")

if not token:
    print("Please set GITHUB_TOKEN environment variable")
    print("Example: export GITHUB_TOKEN=your_token_here")
    sys.exit(1)

# Test configurations
test_configs = [
    {"name": "Conservative", "batch_size": 25, "delay": 0.2, "verbose": True},
    {"name": "Default (Recommended)", "batch_size": 50, "delay": 0.1, "verbose": True},
    {"name": "Fast", "batch_size": 75, "delay": 0.05, "verbose": True},
    {"name": "Ultra Fast", "batch_size": 100, "delay": 0, "verbose": False},
]


def benchmark_config(api, config, test_vendors=5):
    """
    Run a benchmark test with the specific configuration.
    Test only first N vendors to avoid using too much quota.
    """
    print(f"\n{'='*60}")
    print(f"Testing: {config['name']}")
    print(f"Settings: batch_size={config['batch_size']}, delay={config['delay']}s")
    print(f"{'='*60}\n")

    start_time = time.time()

    # Initialize API
    api_test = GitHubGQLAPI(token=api.token, owner=api.owner, repo=api.repo)

    # Fetch tree with timing
    tree = api_test.get_tree(
        batch_size=config["batch_size"],
        delay_between_batches=config["delay"],
        verbose=config["verbose"],
    )

    elapsed = time.time() - start_time

    # Calculate stats
    total_vendors = len(tree)
    total_files = sum(len(files) for files in tree.values())
    files_per_second = total_files / elapsed if elapsed > 0 else 0

    print(f"\n{'-'*60}")
    print(f"Results for {config['name']}:")
    print(f"  Time: {elapsed:.2f} seconds")
    print(f"  Vendors: {total_vendors}")
    print(f"  Files: {total_files}")
    print(f"  Speed: {files_per_second:.1f} files/second")
    print(f"{'-'*60}")

    return {
        "name": config["name"],
        "elapsed": elapsed,
        "vendors": total_vendors,
        "files": total_files,
        "fps": files_per_second,
    }


def main():
    print("GitHub Device Type Import - Performance Benchmark")
    print("=" * 60)

    # Initialize API
    api = GitHubGQLAPI(token=token, owner="netbox-community", repo="devicetype-library")

    # Ask user which tests to run
    print("\nAvailable benchmark tests:")
    for i, config in enumerate(test_configs, 1):
        print(f"  {i}. {config['name']}")
    print(f"  {len(test_configs) + 1}. Run all tests")
    print(f"  {len(test_configs) + 2}. Quick test (default only)")

    choice = input("\nSelect test to run (or press Enter for quick test): ").strip()

    results = []

    if not choice or choice == str(len(test_configs) + 2):
        # Quick test - default only
        results.append(benchmark_config(api, test_configs[1]))
    elif choice == str(len(test_configs) + 1):
        # Run all tests
        for config in test_configs:
            results.append(benchmark_config(api, config))
            if config != test_configs[-1]:
                print("\nWaiting 5 seconds before next test...")
                time.sleep(5)
    else:
        # Run specific test
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(test_configs):
                results.append(benchmark_config(api, test_configs[idx]))
            else:
                print("Invalid selection")
                return
        except ValueError:
            print("Invalid input")
            return

    # Print comparison
    if len(results) > 1:
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON")
        print("=" * 60)
        print(f"{'Configuration':<20} {'Time (s)':<12} {'Files/s':<12} {'Speedup':<10}")
        print("-" * 60)

        baseline = results[0]["elapsed"]
        for result in results:
            speedup = baseline / result["elapsed"] if result["elapsed"] > 0 else 1
            print(
                f"{result['name']:<20} {result['elapsed']:>10.2f}s {result['fps']:>10.1f}  {speedup:>8.2f}×"
            )
        print("=" * 60)


if __name__ == "__main__":
    main()
