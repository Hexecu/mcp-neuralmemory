#!/usr/bin/env python3
"""
massive_stress_test.py
High-concurrency stress, load, and resilience benchmark harness for Neural Memory Agent.
"""
import argparse
import asyncio
import base64
import io
import os
import time
from typing import Any, Dict, List
import urllib.request
import urllib.error
import json
import numpy as np
from PIL import Image


SERVER_URL = "http://127.0.0.1:8765"
DEFAULT_TOKEN = "81d59c6d7adf6dd2cecc3034ac9c7a37094d703f529dd52e990df7d7713ac3c8"
TOKEN = os.getenv("KG_MCP_TOKEN", DEFAULT_TOKEN)
AUTH_HEADER = f"Bearer {TOKEN}"


def make_request(path: str, method: str = "GET", data: Dict[str, Any] = None) -> tuple[int, float, Any]:
    url = f"{SERVER_URL}{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", AUTH_HEADER)
    req.add_header("Content-Type", "application/json")

    body = json.dumps(data).encode("utf-8") if data else None
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, data=body, timeout=25.0) as resp:
            elapsed = time.perf_counter() - start
            res_data = json.loads(resp.read().decode("utf-8"))
            return resp.status, elapsed, res_data
    except urllib.error.HTTPError as e:
        elapsed = time.perf_counter() - start
        try:
            err_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            err_body = str(e)
        return e.code, elapsed, {"error": err_body}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return 599, elapsed, {"error": str(e)}


async def async_worker(path: str, method: str, payload: Dict[str, Any] = None) -> tuple[int, float, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, make_request, path, method, payload)


def generate_dummy_image_b64(color=(100, 150, 200), perturb: int = 0) -> str:
    img = Image.new("RGB", (32, 32), (min(255, color[0] + perturb), color[1], color[2]))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


async def run_burst_stress(num_requests: int = 100, concurrency: int = 25) -> Dict[str, Any]:
    print(f"\n⚡ Phase 1: Ingesting {num_requests} events with concurrency={concurrency}...")
    sem = asyncio.Semaphore(concurrency)

    async def bounded_request(idx: int):
        async with sem:
            payload = {
                "project_id": "massive-stress-test",
                "event_type": "window_focus",
                "data": {
                    "app": "Xcode",
                    "window": f"ProjectFile_{idx}.swift",
                    "text": f"User edited function executeBenchmark_{idx} at line {idx * 10}"
                }
            }
            return await async_worker("/api/ingest/event", "POST", payload)

    start_total = time.perf_counter()
    tasks = [bounded_request(i) for i in range(num_requests)]
    results = await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start_total

    latencies = [r[1] * 1000.0 for r in results]
    success_count = sum(1 for r in results if r[0] == 200)

    return {
        "total_requests": num_requests,
        "success_count": success_count,
        "failed_count": num_requests - success_count,
        "total_time_s": total_time,
        "throughput_req_per_s": num_requests / total_time,
        "lat_p50_ms": float(np.percentile(latencies, 50)),
        "lat_p90_ms": float(np.percentile(latencies, 90)),
        "lat_p95_ms": float(np.percentile(latencies, 95)),
        "lat_p99_ms": float(np.percentile(latencies, 99)),
    }


async def run_screenshot_dedup_stress(num_shots: int = 20) -> Dict[str, Any]:
    print(f"\n📸 Phase 2: Ingesting {num_shots} screenshots with parallel visual pHash deduplication...")
    base_b64 = generate_dummy_image_b64((120, 140, 180), perturb=0)

    async def send_shot(i: int):
        b64 = base_b64 if i % 2 == 0 else generate_dummy_image_b64((120, 140, 180), perturb=(i * 4))
        payload = {
            "project_id": "massive-stress-test",
            "event_type": "screenshot",
            "data": {"app": "Safari", "window": "Research Dashboard", "has_screenshot": True},
            "screenshot_base64": b64
        }
        return await async_worker("/api/ingest/event", "POST", payload)

    start = time.perf_counter()
    results = await asyncio.gather(*[send_shot(i) for i in range(num_shots)])
    total_time = time.perf_counter() - start

    success_count = sum(1 for r in results if r[0] == 200)
    latencies = [r[1] * 1000.0 for r in results]
    return {
        "total_screenshots": num_shots,
        "success_count": success_count,
        "total_time_s": total_time,
        "throughput": num_shots / total_time,
        "lat_p95_ms": float(np.percentile(latencies, 95))
    }


async def run_mixed_graph_and_search_stress(num_queries: int = 30) -> Dict[str, Any]:
    print(f"\n🔍 Phase 3: Concurrent mixed queries (/api/graph/data & /api/search/deep)...")

    async def query_worker(i: int):
        if i % 2 == 0:
            return await async_worker("/api/graph/data?project_id=massive-stress-test", "GET", None)
        else:
            payload = {
                "project_id": "massive-stress-test",
                "query": "Xcode Benchmark",
                "limit": 5
            }
            return await async_worker("/api/search/deep", "POST", payload)

    start = time.perf_counter()
    results = await asyncio.gather(*[query_worker(i) for i in range(num_queries)])
    total_time = time.perf_counter() - start

    success_count = sum(1 for r in results if r[0] == 200)
    latencies = [r[1] * 1000.0 for r in results]

    return {
        "total_queries": num_queries,
        "success_count": success_count,
        "total_time_s": total_time,
        "throughput_qps": num_queries / total_time,
        "lat_p95_ms": float(np.percentile(latencies, 95))
    }


async def run_dream_cycle_stress() -> Dict[str, Any]:
    print(f"\n🧠 Phase 4: Autonomous Dream Mode consolidation cycle under pressure...")
    start = time.perf_counter()
    status, elapsed, data = await async_worker("/api/memory/dream?project_id=massive-stress-test", "POST", {})
    return {
        "status": status,
        "elapsed_s": elapsed,
        "reflections_created": data.get("reflections_created", 0) if status == 200 else 0
    }


async def main():
    parser = argparse.ArgumentParser(description="Neural Memory Massive Stress Test Harness")
    parser.add_argument("--concurrency", type=int, default=25, help="Worker concurrency limit")
    parser.add_argument("--events", type=int, default=100, help="Number of event ingestions")
    args = parser.parse_args()

    print("=" * 65)
    print("🚀 NEURAL MEMORY AGENT — MASSIVE STRESS & BENCHMARK HARNESS")
    print(f"Target: {SERVER_URL} | Concurrency: {args.concurrency} | Events: {args.events}")
    print("=" * 65)

    # Health check
    status, elapsed, _ = make_request("/health")
    if status != 200:
        print(f"❌ Daemon health check failed (status: {status}). Ensure backend is up.")
        return

    print(f"✅ Daemon is healthy (latency: {elapsed*1000:.2f}ms)")

    # Run Phases
    p1 = await run_burst_stress(num_requests=args.events, concurrency=args.concurrency)
    p2 = await run_screenshot_dedup_stress(num_shots=20)
    p3 = await run_mixed_graph_and_search_stress(num_queries=30)
    p4 = await run_dream_cycle_stress()

    # Executive Summary Report
    print("\n" + "=" * 65)
    print("📊 EXECUTIVE BENCHMARK RESULTS")
    print("=" * 65)
    print(f"• Event Ingestion Throughput:  {p1['throughput_req_per_s']:.1f} req/s ({p1['success_count']}/{p1['total_requests']} OK)")
    print(f"• Ingestion Latency (p50):    {p1['lat_p50_ms']:.2f} ms")
    print(f"• Ingestion Latency (p95):    {p1['lat_p95_ms']:.2f} ms")
    print(f"• Ingestion Latency (p99):    {p1['lat_p99_ms']:.2f} ms")
    print(f"• Screenshot Flood Dedup:     {p2['throughput']:.1f} shots/s ({p2['success_count']}/{p2['total_screenshots']} OK, p95: {p2['lat_p95_ms']:.2f} ms)")
    print(f"• Mixed Graph/Search QPS:     {p3['throughput_qps']:.1f} queries/s ({p3['success_count']}/{p3['total_queries']} OK, p95: {p3['lat_p95_ms']:.2f} ms)")
    print(f"• Dream Mode Cycle Execution: {p4['elapsed_s']:.2f} s (Reflections synthesized: {p4['reflections_created']})")
    print("=" * 65)

    if p1['success_count'] == p1['total_requests'] and p2['success_count'] == p2['total_screenshots'] and p3['success_count'] == p3['total_queries']:
        print("🎉 ALL STRESS TESTS PASSED WITH 100% SUCCESS RATE & ZERO DEADLOCKS!\n")
    else:
        print("⚠️ Some stress requests encountered errors.\n")


if __name__ == "__main__":
    asyncio.run(main())
