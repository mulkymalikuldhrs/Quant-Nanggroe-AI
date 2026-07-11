#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║      Quant-Nanggroe-AI  —  Load Testing Script                      ║
║      Concurrent Requests, Throughput, Latency, Error Tracking       ║
╚══════════════════════════════════════════════════════════════════════╝

Usage:
    python scripts/load_test.py --url http://localhost:8000 --concurrent 50 --duration 60
    python scripts/load_test.py --url http://localhost:8000 --endpoints /health /ready /api/v1/kelly/calculate
    python scripts/load_test.py --url http://localhost:8000 --report report.json
"""

import argparse
import json
import os
import statistics
import sys
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library required. Install with: pip install requests")
    sys.exit(1)


# ── Data Models ────────────────────────────────────────────────────────

@dataclass
class RequestResult:
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    response_size: int
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class EndpointStats:
    endpoint: str
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    latency_samples: list = field(default_factory=list)
    error_counts: dict = field(default_factory=lambda: defaultdict(int))
    status_counts: dict = field(default_factory=lambda: defaultdict(int))


@dataclass
class LoadTestReport:
    test_id: str
    target_url: str
    start_time: str
    end_time: str
    duration_seconds: float
    total_requests: int
    total_errors: int
    error_rate: float
    requests_per_second: float
    latency_p50: float
    latency_p90: float
    latency_p95: float
    latency_p99: float
    latency_mean: float
    latency_stdev: float
    latency_min: float
    latency_max: float
    throughput_mbps: float
    endpoints: dict
    error_summary: dict


# ── Load Tester ────────────────────────────────────────────────────────

class LoadTester:
    def __init__(self, base_url: str, concurrent: int, duration: int,
                 endpoints: list, timeout: int = 30, rate_limit: int = 0):
        self.base_url = base_url.rstrip("/")
        self.concurrent = concurrent
        self.duration = duration
        self.endpoints = endpoints
        self.timeout = timeout
        self.rate_limit = rate_limit  # 0 = unlimited
        self.results: list[RequestResult] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._request_count = 0
        self._start_time = 0.0

    def _send_request(self, endpoint: str, method: str = "GET") -> RequestResult:
        url = f"{self.base_url}{endpoint}"
        try:
            start = time.perf_counter()
            if method == "GET":
                resp = requests.get(url, timeout=self.timeout)
            elif method == "POST":
                resp = requests.post(url, json=self._get_post_body(endpoint),
                                     timeout=self.timeout)
            else:
                resp = requests.request(method, url, timeout=self.timeout)
            latency = (time.perf_counter() - start) * 1000

            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=resp.status_code,
                latency_ms=latency,
                response_size=len(resp.content),
                error=None if resp.status_code < 500 else f"HTTP {resp.status_code}",
            )
        except requests.exceptions.Timeout:
            return RequestResult(
                endpoint=endpoint, method=method, status_code=0,
                latency_ms=self.timeout * 1000, response_size=0,
                error="Timeout",
            )
        except requests.exceptions.ConnectionError as e:
            return RequestResult(
                endpoint=endpoint, method=method, status_code=0,
                latency_ms=0, response_size=0,
                error=f"ConnectionError: {str(e)[:100]}",
            )
        except Exception as e:
            return RequestResult(
                endpoint=endpoint, method=method, status_code=0,
                latency_ms=0, response_size=0,
                error=f"Exception: {str(e)[:100]}",
            )

    def _get_post_body(self, endpoint: str) -> dict:
        """Return appropriate POST body for known endpoints."""
        if "kelly" in endpoint:
            return {"symbol": "AAPL", "capital": 100000, "method": "fractional"}
        elif "regime" in endpoint:
            return {"symbol": "SPY"}
        elif "stress" in endpoint:
            return {"portfolio": {"AAPL": 0.5, "GOOGL": 0.5}, "scenarios": 100}
        return {}

    def _worker(self):
        """Single worker thread: send requests until stopped."""
        while not self._stop_event.is_set():
            endpoint = self.endpoints[self._request_count % len(self.endpoints)]
            method = "POST" if any(k in endpoint for k in ["kelly", "regime", "stress"]) else "GET"
            result = self._send_request(endpoint, method)

            with self._lock:
                self.results.append(result)
                self._request_count += 1

            if self.rate_limit > 0:
                time.sleep(1.0 / self.rate_limit)

    def run(self) -> LoadTestReport:
        """Execute the load test and return a report."""
        test_id = f"loadtest-{int(time.time())}"
        self._start_time = time.time()

        print(f"\n{'='*60}")
        print(f"  Quant-Nanggroe-AI Load Test")
        print(f"{'='*60}")
        print(f"  Target:      {self.base_url}")
        print(f"  Endpoints:   {', '.join(self.endpoints)}")
        print(f"  Concurrent:  {self.concurrent} threads")
        print(f"  Duration:    {self.duration}s")
        print(f"  Rate Limit:  {'Unlimited' if self.rate_limit == 0 else f'{self.rate_limit} req/s'}")
        print(f"{'='*60}\n")

        # Launch workers
        with ThreadPoolExecutor(max_workers=self.concurrent) as pool:
            futures = [pool.submit(self._worker) for _ in range(self.concurrent)]

            # Wait for duration
            try:
                for _ in range(self.duration):
                    time.sleep(1)
                    elapsed = time.time() - self._start_time
                    with self._lock:
                        rps = len(self.results) / max(elapsed, 0.001)
                    sys.stdout.write(f"\r  Elapsed: {int(elapsed)}s | Requests: {len(self.results)} | RPS: {rps:.1f}  ")
                    sys.stdout.flush()
            except KeyboardInterrupt:
                print("\n\n  Test interrupted by user")

            self._stop_event.set()
            for f in futures:
                f.cancel()

        print()  # Newline after progress

        # Generate report
        return self._generate_report(test_id)

    def _generate_report(self, test_id: str) -> LoadTestReport:
        """Aggregate results into a structured report."""
        end_time = time.time()
        duration = end_time - self._start_time

        latencies = [r.latency_ms for r in self.results]
        errors = [r for r in self.results if r.error is not None]
        total_bytes = sum(r.response_size for r in self.results)

        # Endpoint-level stats
        endpoint_stats = {}
        endpoints_grouped = defaultdict(list)
        for r in self.results:
            endpoints_grouped[r.endpoint].append(r)

        for ep, reqs in endpoints_grouped.items():
            ep_latencies = [r.latency_ms for r in reqs]
            ep_errors = [r for r in reqs if r.error]
            endpoint_stats[ep] = {
                "total": len(reqs),
                "successful": len(reqs) - len(ep_errors),
                "failed": len(ep_errors),
                "error_rate": len(ep_errors) / max(len(reqs), 1),
                "latency_p50": statistics.median(ep_latencies) if ep_latencies else 0,
                "latency_p95": (sorted(ep_latencies)[int(len(ep_latencies) * 0.95)]
                                if len(ep_latencies) >= 2 else (ep_latencies[0] if ep_latencies else 0)),
                "latency_mean": statistics.mean(ep_latencies) if ep_latencies else 0,
            }

        # Error summary
        error_summary = defaultdict(int)
        for r in errors:
            error_summary[r.error] += 1

        sorted_lat = sorted(latencies) if latencies else [0]
        n = len(sorted_lat)

        report = LoadTestReport(
            test_id=test_id,
            target_url=self.base_url,
            start_time=datetime.fromtimestamp(self._start_time, tz=timezone.utc).isoformat(),
            end_time=datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat(),
            duration_seconds=round(duration, 2),
            total_requests=len(self.results),
            total_errors=len(errors),
            error_rate=round(len(errors) / max(len(self.results), 1), 4),
            requests_per_second=round(len(self.results) / max(duration, 0.001), 2),
            latency_p50=round(sorted_lat[n // 2], 2),
            latency_p90=round(sorted_lat[int(n * 0.9)], 2),
            latency_p95=round(sorted_lat[int(n * 0.95)], 2),
            latency_p99=round(sorted_lat[int(n * 0.99)], 2),
            latency_mean=round(statistics.mean(latencies), 2) if latencies else 0,
            latency_stdev=round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0,
            latency_min=round(sorted_lat[0], 2),
            latency_max=round(sorted_lat[-1], 2),
            throughput_mbps=round((total_bytes / 1024 / 1024) / max(duration, 0.001), 4),
            endpoints=endpoint_stats,
            error_summary=dict(error_summary),
        )

        self._print_report(report)
        return report

    def _print_report(self, report: LoadTestReport):
        """Print human-readable report to stdout."""
        print(f"\n{'='*60}")
        print(f"  LOAD TEST REPORT — {report.test_id}")
        print(f"{'='*60}")
        print(f"  Target:            {report.target_url}")
        print(f"  Duration:          {report.duration_seconds}s")
        print(f"  Total Requests:    {report.total_requests}")
        print(f"  Errors:            {report.total_errors} ({report.error_rate:.2%})")
        print(f"  Throughput:        {report.requests_per_second} req/s ({report.throughput_mbps} MB/s)")
        print()
        print(f"  Latency Distribution:")
        print(f"    Min:             {report.latency_min}ms")
        print(f"    P50:             {report.latency_p50}ms")
        print(f"    P90:             {report.latency_p90}ms")
        print(f"    P95:             {report.latency_p95}ms")
        print(f"    P99:             {report.latency_p99}ms")
        print(f"    Max:             {report.latency_max}ms")
        print(f"    Mean:            {report.latency_mean}ms")
        print(f"    Stdev:           {report.latency_stdev}ms")
        print()

        if report.endpoints:
            print(f"  Per-Endpoint Breakdown:")
            for ep, stats in report.endpoints.items():
                print(f"    {ep}")
                print(f"      Requests: {stats['total']} | OK: {stats['successful']} | Fail: {stats['failed']}")
                print(f"      P50: {stats['latency_p50']}ms | P95: {stats['latency_p95']}ms | Mean: {stats['latency_mean']}ms")
            print()

        if report.error_summary:
            print(f"  Error Summary:")
            for err, count in sorted(report.error_summary.items(), key=lambda x: -x[1]):
                print(f"    {err}: {count}")

        print(f"{'='*60}\n")


# ── CLI ────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Quant-Nanggroe-AI Load Testing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url http://localhost:8000 --concurrent 50 --duration 60
  %(prog)s --url http://localhost:8000 --endpoints /health /ready
  %(prog)s --url http://localhost:8000 --report results.json
        """,
    )
    parser.add_argument("--url", default="http://localhost:8000",
                        help="Target URL (default: http://localhost:8000)")
    parser.add_argument("--concurrent", "-c", type=int, default=10,
                        help="Concurrent threads (default: 10)")
    parser.add_argument("--duration", "-d", type=int, default=30,
                        help="Test duration in seconds (default: 30)")
    parser.add_argument("--endpoints", "-e", nargs="+",
                        default=["/health", "/ready", "/live"],
                        help="Endpoints to test")
    parser.add_argument("--timeout", "-t", type=int, default=30,
                        help="Request timeout in seconds (default: 30)")
    parser.add_argument("--rate-limit", "-r", type=int, default=0,
                        help="Requests per second limit (0=unlimited)")
    parser.add_argument("--report", "-o",
                        help="Save JSON report to file")
    return parser.parse_args()


def main():
    args = parse_args()

    tester = LoadTester(
        base_url=args.url,
        concurrent=args.concurrent,
        duration=args.duration,
        endpoints=args.endpoints,
        timeout=args.timeout,
        rate_limit=args.rate_limit,
    )

    report = tester.run()

    if args.report:
        with open(args.report, "w") as f:
            json.dump(asdict(report), f, indent=2, default=str)
        print(f"  Report saved to: {args.report}")

    # Exit code: 1 if error rate > 10%
    sys.exit(1 if report.error_rate > 0.10 else 0)


if __name__ == "__main__":
    main()
