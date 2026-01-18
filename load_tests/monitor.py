#!/usr/bin/env python3
"""
Performance Monitoring Utility for Load Tests

Real-time monitoring of system metrics during load testing:
- API response times
- System resources (CPU, memory, disk)
- Database connection pool status
- Redis cache statistics
- Error rates

Usage:
    python load_tests/monitor.py --host http://localhost:8000 --interval 5

Arguments:
    --host: API host URL (default: http://localhost:8000)
    --interval: Polling interval in seconds (default: 5)
    --duration: Monitoring duration in seconds (default: infinite)
    --output: Output CSV file for metrics (optional)
"""

import argparse
import asyncio
import csv
import sys
import time
from datetime import datetime
from typing import Optional

import httpx
import psutil


class PerformanceMonitor:
    """Real-time performance monitoring for load tests"""

    def __init__(self, api_host: str, interval: int = 5, output_file: Optional[str] = None):
        self.api_host = api_host.rstrip("/")
        self.interval = interval
        self.output_file = output_file
        self.csv_writer = None
        self.csv_file = None

        # Metrics storage
        self.metrics_history = []

        # HTTP client
        self.client = httpx.AsyncClient(timeout=10.0)

    async def start(self, duration: Optional[int] = None):
        """Start monitoring"""
        print("=" * 80)
        print("🔍 PERFORMANCE MONITORING STARTED")
        print("=" * 80)
        print(f"API Host: {self.api_host}")
        print(f"Interval: {self.interval}s")
        if duration:
            print(f"Duration: {duration}s")
        else:
            print("Duration: Infinite (Ctrl+C to stop)")
        print("=" * 80)
        print()

        # Setup CSV output if specified
        if self.output_file:
            self.csv_file = open(self.output_file, "w", newline="")
            fieldnames = [
                "timestamp",
                "cpu_percent",
                "memory_mb",
                "memory_percent",
                "disk_read_mb",
                "disk_write_mb",
                "network_sent_mb",
                "network_recv_mb",
                "api_latency_ms",
                "api_status",
                "db_pool_size",
                "db_pool_available",
                "db_pool_active",
                "redis_hit_rate",
                "redis_total_reads",
            ]
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
            self.csv_writer.writeheader()
            print(f"📊 Metrics will be saved to: {self.output_file}")
            print()

        # Print header
        self._print_header()

        # Monitoring loop
        start_time = time.time()
        try:
            while True:
                # Check duration
                if duration and (time.time() - start_time) >= duration:
                    break

                # Collect metrics
                metrics = await self._collect_metrics()

                # Store metrics
                self.metrics_history.append(metrics)

                # Print metrics
                self._print_metrics(metrics)

                # Write to CSV
                if self.csv_writer:
                    self.csv_writer.writerow(metrics)
                    self.csv_file.flush()

                # Wait for next interval
                await asyncio.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\n⏸️  Monitoring stopped by user")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()
        if self.csv_file:
            self.csv_file.close()

        # Print summary
        self._print_summary()

    def _print_header(self):
        """Print metrics table header"""
        print(
            f"{'Time':<10} | {'CPU%':<6} | {'Mem%':<6} | {'Mem(MB)':<8} | "
            f"{'API(ms)':<8} | {'DB Pool':<10} | {'Redis Hit%':<10} | {'Status':<8}"
        )
        print("-" * 90)

    def _print_metrics(self, metrics: dict):
        """Print current metrics"""
        timestamp = metrics["timestamp"]
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

        cpu = metrics["cpu_percent"]
        mem_pct = metrics["memory_percent"]
        mem_mb = metrics["memory_mb"]
        api_latency = metrics["api_latency_ms"]
        api_status = metrics["api_status"]

        # Database pool
        db_pool_str = f"{metrics['db_pool_active']}/{metrics['db_pool_size']}"

        # Redis hit rate
        redis_hit_rate = metrics["redis_hit_rate"]
        redis_str = f"{redis_hit_rate:.1f}%" if redis_hit_rate is not None else "N/A"

        # Status emoji
        status_emoji = "✅" if api_status == 200 else "❌"

        print(
            f"{time_str:<10} | {cpu:>5.1f}% | {mem_pct:>5.1f}% | {mem_mb:>7.0f} | "
            f"{api_latency:>7.0f} | {db_pool_str:<10} | {redis_str:<10} | {status_emoji} {api_status}"
        )

    async def _collect_metrics(self) -> dict:
        """Collect all performance metrics"""
        timestamp = time.time()

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        network_io = psutil.net_io_counters()

        # API health check with latency measurement
        api_latency_ms = None
        api_status = None
        try:
            start = time.perf_counter()
            response = await self.client.get(f"{self.api_host}/health")
            api_latency_ms = (time.perf_counter() - start) * 1000
            api_status = response.status_code
        except Exception as e:
            api_latency_ms = -1
            api_status = 0

        # Database pool stats (from metrics endpoint)
        db_pool_size = 0
        db_pool_available = 0
        db_pool_active = 0
        try:
            response = await self.client.get(f"{self.api_host}/api/v1/metrics")
            if response.status_code == 200:
                data = response.json()
                db_pool_size = data.get("database", {}).get("pool_size", 0)
                db_pool_available = data.get("database", {}).get("pool_available", 0)
                db_pool_active = data.get("database", {}).get("pool_active", 0)
        except Exception:
            pass

        # Redis cache stats (from metrics endpoint)
        redis_hit_rate = None
        redis_total_reads = 0
        try:
            response = await self.client.get(f"{self.api_host}/api/v1/metrics")
            if response.status_code == 200:
                data = response.json()
                cache_stats = data.get("cache", {})
                redis_hit_rate = cache_stats.get("hit_rate_percent")
                redis_total_reads = cache_stats.get("total_reads", 0)
        except Exception:
            pass

        return {
            "timestamp": timestamp,
            "cpu_percent": cpu_percent,
            "memory_mb": memory.used / 1024 / 1024,
            "memory_percent": memory.percent,
            "disk_read_mb": disk_io.read_bytes / 1024 / 1024,
            "disk_write_mb": disk_io.write_bytes / 1024 / 1024,
            "network_sent_mb": network_io.bytes_sent / 1024 / 1024,
            "network_recv_mb": network_io.bytes_recv / 1024 / 1024,
            "api_latency_ms": api_latency_ms if api_latency_ms else 0,
            "api_status": api_status if api_status else 0,
            "db_pool_size": db_pool_size,
            "db_pool_available": db_pool_available,
            "db_pool_active": db_pool_active,
            "redis_hit_rate": redis_hit_rate,
            "redis_total_reads": redis_total_reads,
        }

    def _print_summary(self):
        """Print monitoring summary"""
        if not self.metrics_history:
            return

        print("\n")
        print("=" * 80)
        print("📊 MONITORING SUMMARY")
        print("=" * 80)

        # Calculate statistics
        cpu_values = [m["cpu_percent"] for m in self.metrics_history]
        mem_values = [m["memory_mb"] for m in self.metrics_history]
        api_latencies = [m["api_latency_ms"] for m in self.metrics_history if m["api_latency_ms"] > 0]

        # CPU stats
        print(f"\n🖥️  CPU Usage:")
        print(f"   Average: {sum(cpu_values) / len(cpu_values):.1f}%")
        print(f"   Min: {min(cpu_values):.1f}%")
        print(f"   Max: {max(cpu_values):.1f}%")

        # Memory stats
        print(f"\n💾 Memory Usage:")
        print(f"   Average: {sum(mem_values) / len(mem_values):.0f} MB")
        print(f"   Min: {min(mem_values):.0f} MB")
        print(f"   Max: {max(mem_values):.0f} MB")

        # API latency stats
        if api_latencies:
            sorted_latencies = sorted(api_latencies)
            p50_index = int(len(sorted_latencies) * 0.5)
            p95_index = int(len(sorted_latencies) * 0.95)
            p99_index = int(len(sorted_latencies) * 0.99)

            print(f"\n🌐 API Latency:")
            print(f"   Average: {sum(api_latencies) / len(api_latencies):.0f} ms")
            print(f"   P50: {sorted_latencies[p50_index]:.0f} ms")
            print(f"   P95: {sorted_latencies[p95_index]:.0f} ms")
            print(f"   P99: {sorted_latencies[p99_index]:.0f} ms")

        # Error count
        errors = sum(1 for m in self.metrics_history if m["api_status"] != 200)
        error_rate = (errors / len(self.metrics_history)) * 100
        print(f"\n⚠️  API Errors:")
        print(f"   Total: {errors}")
        print(f"   Rate: {error_rate:.2f}%")

        # Redis cache performance
        redis_metrics = [m for m in self.metrics_history if m["redis_hit_rate"] is not None]
        if redis_metrics:
            avg_hit_rate = sum(m["redis_hit_rate"] for m in redis_metrics) / len(redis_metrics)
            print(f"\n📦 Redis Cache:")
            print(f"   Average hit rate: {avg_hit_rate:.1f}%")

        # Database pool
        db_metrics = [m for m in self.metrics_history if m["db_pool_size"] > 0]
        if db_metrics:
            avg_active = sum(m["db_pool_active"] for m in db_metrics) / len(db_metrics)
            max_active = max(m["db_pool_active"] for m in db_metrics)
            pool_size = self.metrics_history[-1]["db_pool_size"]
            print(f"\n🗄️  Database Pool:")
            print(f"   Pool size: {pool_size}")
            print(f"   Average active: {avg_active:.1f}")
            print(f"   Peak active: {max_active}")

        print("\n" + "=" * 80)
        print(f"Total samples: {len(self.metrics_history)}")
        print(f"Monitoring duration: {len(self.metrics_history) * self.interval}s")
        print("=" * 80 + "\n")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Performance monitoring for load tests")
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="API host URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Monitoring duration in seconds (default: infinite)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV file for metrics (optional)",
    )

    args = parser.parse_args()

    monitor = PerformanceMonitor(
        api_host=args.host,
        interval=args.interval,
        output_file=args.output,
    )

    await monitor.start(duration=args.duration)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
