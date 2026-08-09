"""
Load Testing Script for Movie Rating API.

This script generates load on the API to test metrics collection
and visualization in Grafana.

Usage:
    python scripts/load_test.py
    python scripts/load_test.py --duration 120 --workers 20
    python scripts/load_test.py --batch
    python scripts/load_test.py --variable --duration 120 --workers 50
    python scripts/load_test.py --spike --workers 5
"""

import argparse
import concurrent.futures
import random
import time
from typing import List, Tuple

import requests

# API Configuration
API_URL = "http://localhost:8000"


def make_single_prediction() -> Tuple[bool, float]:
    """
    Make a single prediction request.

    Returns:
        Tuple of (success: bool, latency_ms: float)
    """
    # Generate random user and movie IDs
    # MovieLens 100K has users 1-943 and movies 1-1682
    user_id = str(random.randint(1, 943))
    movie_id = str(random.randint(1, 1682))

    start_time = time.time()

    try:
        response = requests.post(
            f"{API_URL}/predict",
            json={"user_id": user_id, "movie_id": movie_id},
            timeout=5
        )
        latency_ms = (time.time() - start_time) * 1000
        return response.status_code == 200, latency_ms
    except Exception:
        latency_ms = (time.time() - start_time) * 1000
        return False, latency_ms


def make_batch_prediction(batch_size: int = 10) -> Tuple[bool, float]:
    """
    Make a batch prediction request.

    Args:
        batch_size: Number of predictions in the batch

    Returns:
        Tuple of (success: bool, latency_ms: float)
    """
    predictions = [
        {
            "user_id": str(random.randint(1, 943)),
            "movie_id": str(random.randint(1, 1682))
        }
        for _ in range(batch_size)
    ]

    start_time = time.time()

    try:
        response = requests.post(
            f"{API_URL}/predict/batch",
            json={"predictions": predictions},
            timeout=10
        )
        latency_ms = (time.time() - start_time) * 1000
        return response.status_code == 200, latency_ms
    except Exception:
        latency_ms = (time.time() - start_time) * 1000
        return False, latency_ms


def check_health() -> bool:
    """Check if the API is healthy."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


# =============================================================================
# TODO 1: run_load_test
# =============================================================================

def run_load_test(duration: int = 60, workers: int = 10, batch_mode: bool = False):
    """
    Run load test for specified duration.

    1. Checks API health before starting
    2. Uses ThreadPoolExecutor for concurrent requests
    3. Tracks total requests, successful requests, and latencies
    4. Prints progress every ~10 seconds
    5. Prints final statistics

    Args:
        duration: Test duration in seconds
        workers: Number of concurrent workers
        batch_mode: If True, use batch predictions
    """
    print("=" * 60)
    print("Load Test for Movie Rating API")
    print("=" * 60)
    print(f"Duration: {duration}s")
    print(f"Workers: {workers}")
    print(f"Mode: {'Batch' if batch_mode else 'Single'}")
    print("=" * 60)

    # 1. Check API health
    if not check_health():
        print("ERROR: API is not healthy. Aborting load test.")
        return

    # 2. Initialize counters
    total_requests = 0
    successful = 0
    latencies: List[float] = []

    # 3. Run load test using ThreadPoolExecutor
    start_time = time.time()
    last_progress = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        while time.time() - start_time < duration:
            # Submit one wave of tasks (one per worker)
            if batch_mode:
                futures = [executor.submit(make_batch_prediction) for _ in range(workers)]
            else:
                futures = [executor.submit(make_single_prediction) for _ in range(workers)]

            # Collect results
            for future in concurrent.futures.as_completed(futures):
                success, latency = future.result()
                total_requests += 1
                if success:
                    successful += 1
                latencies.append(latency)

            # Progress update every ~10 seconds
            elapsed = time.time() - start_time
            if int(elapsed) // 10 > last_progress:
                last_progress = int(elapsed) // 10
                rps = total_requests / elapsed if elapsed > 0 else 0
                print(f"  Progress: {int(elapsed):>3}s - {total_requests} requests "
                      f"({rps:.1f} req/s, {successful} ok)")

            # Small delay to control rate
            time.sleep(0.1)

    # 4. Print statistics
    actual_duration = max(time.time() - start_time, 1e-9)
    print_statistics(total_requests, successful, latencies, int(actual_duration))


def print_statistics(total: int, successful: int, latencies: list, duration: int):
    """Print load test statistics."""
    import statistics

    print("\n" + "=" * 60)
    print("Load Test Results")
    print("=" * 60)
    print(f"Total Requests:    {total}")
    print(f"Successful:        {successful}")
    print(f"Failed:            {total - successful}")
    print(f"Success Rate:      {successful/total*100:.2f}%" if total > 0 else "N/A")
    print(f"Requests/Second:   {total/duration:.2f}")

    if latencies:
        print(f"\nLatency Statistics (ms):")
        print(f"  Min:    {min(latencies):.2f}")
        print(f"  Max:    {max(latencies):.2f}")
        print(f"  Mean:   {statistics.mean(latencies):.2f}")
        print(f"  Median: {statistics.median(latencies):.2f}")
        if len(latencies) > 1:
            print(f"  StdDev: {statistics.stdev(latencies):.2f}")

        # Percentiles
        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[int(len(sorted_latencies) * 0.5)]
        p95 = sorted_latencies[min(int(len(sorted_latencies) * 0.95), len(sorted_latencies) - 1)]
        p99 = sorted_latencies[min(int(len(sorted_latencies) * 0.99), len(sorted_latencies) - 1)]
        print(f"  P50:    {p50:.2f}")
        print(f"  P95:    {p95:.2f}")
        print(f"  P99:    {p99:.2f}")

    print("=" * 60)


# =============================================================================
# Internal helper: run one load phase at a fixed worker count
# =============================================================================

def _run_phase(workers: int, phase_duration: float,
               stats: dict, batch_mode: bool = False) -> None:
    """Run a load phase with a fixed number of workers, accumulating stats."""
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(workers, 1)) as executor:
        while time.time() - start < phase_duration:
            if batch_mode:
                futures = [executor.submit(make_batch_prediction) for _ in range(workers)]
            else:
                futures = [executor.submit(make_single_prediction) for _ in range(workers)]
            for future in concurrent.futures.as_completed(futures):
                success, latency = future.result()
                stats["total"] += 1
                if success:
                    stats["successful"] += 1
                stats["latencies"].append(latency)
            time.sleep(0.1)


# =============================================================================
# TODO 2: Variable load pattern (BONUS)
# =============================================================================

def run_variable_load(duration: int = 120, max_workers: int = 50):
    """
    Run load test with variable load pattern:
    1. Ramps up from 1 to max_workers over the first quarter of the duration
    2. Maintains max load for half of the duration
    3. Ramps down to 1 worker over the last quarter

    This tests how the system handles varying load.
    """
    print("=" * 60)
    print("Variable Load Test (ramp-up -> sustain -> ramp-down)")
    print("=" * 60)
    print(f"Total duration: {duration}s | Max workers: {max_workers}")

    if not check_health():
        print("ERROR: API is not healthy. Aborting load test.")
        return

    ramp_duration = duration / 4          # e.g. 30s for duration=120
    sustain_duration = duration / 2       # e.g. 60s
    ramp_steps = 5                        # ramp in 5 discrete steps
    step_time = ramp_duration / ramp_steps

    stats = {"total": 0, "successful": 0, "latencies": []}
    start = time.time()

    # Phase 1: Ramp up 1 -> max_workers
    print(f"\n[Phase 1] Ramping up over {ramp_duration:.0f}s...")
    for i in range(1, ramp_steps + 1):
        workers = max(1, int(max_workers * i / ramp_steps))
        print(f"  Step {i}/{ramp_steps}: {workers} workers")
        _run_phase(workers, step_time, stats)

    # Phase 2: Sustain max load
    print(f"\n[Phase 2] Sustaining {max_workers} workers for {sustain_duration:.0f}s...")
    _run_phase(max_workers, sustain_duration, stats)

    # Phase 3: Ramp down max_workers -> 1
    print(f"\n[Phase 3] Ramping down over {ramp_duration:.0f}s...")
    for i in range(ramp_steps, 0, -1):
        workers = max(1, int(max_workers * i / ramp_steps))
        print(f"  Step {ramp_steps - i + 1}/{ramp_steps}: {workers} workers")
        _run_phase(workers, step_time, stats)

    actual_duration = max(int(time.time() - start), 1)
    print_statistics(stats["total"], stats["successful"], stats["latencies"], actual_duration)


# =============================================================================
# TODO 3: Spike test (BONUS)
# =============================================================================

def run_spike_test(normal_workers: int = 5, spike_workers: int = 100, spike_duration: int = 10):
    """
    Run spike test to test system resilience:
    1. Runs normal load for 30 seconds
    2. Spikes to high load for spike_duration
    3. Returns to normal load for 30 seconds

    This tests how the system handles sudden load increases.
    """
    print("=" * 60)
    print("Spike Test (normal -> spike -> normal)")
    print("=" * 60)
    print(f"Normal: {normal_workers} workers | Spike: {spike_workers} workers "
          f"for {spike_duration}s")

    if not check_health():
        print("ERROR: API is not healthy. Aborting load test.")
        return

    stats = {"total": 0, "successful": 0, "latencies": []}
    start = time.time()

    print("\n[Phase 1] Normal load (30s)...")
    _run_phase(normal_workers, 30, stats)
    before_spike = stats["total"]

    print(f"\n[Phase 2] SPIKE to {spike_workers} workers ({spike_duration}s)...")
    _run_phase(spike_workers, spike_duration, stats)
    during_spike = stats["total"] - before_spike

    print("\n[Phase 3] Back to normal load (30s)...")
    _run_phase(normal_workers, 30, stats)

    actual_duration = max(int(time.time() - start), 1)
    print(f"\nRequests during spike window: {during_spike}")
    print_statistics(stats["total"], stats["successful"], stats["latencies"], actual_duration)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Load test the Movie Rating API")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent workers")
    parser.add_argument("--batch", action="store_true", help="Use batch predictions")
    parser.add_argument("--variable", action="store_true", help="Run variable load pattern")
    parser.add_argument("--spike", action="store_true", help="Run spike test")

    args = parser.parse_args()

    if args.variable:
        run_variable_load(args.duration, args.workers)
    elif args.spike:
        run_spike_test(normal_workers=args.workers)
    else:
        run_load_test(args.duration, args.workers, args.batch)


if __name__ == "__main__":
    main()
