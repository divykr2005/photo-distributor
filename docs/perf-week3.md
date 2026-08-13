# Week 3 Performance & Capacity Benchmark

| Metric | Target Budget | Benchmark Result | Status |
|---|---|---|---|
| Token Validation Latency | ≤ 30 ms p95 | 4 ms p95 | PASSED |
| Portal First Paint (24 thumbs) | ≤ 2.0 s p95 | 1.1 s p95 | PASSED |
| Media Serve Latency (thumb) | ≤ 120 ms p95 | 18 ms p95 | PASSED |
| Ephemeral Selfie Embedding | ≤ 800 ms p95 | 240 ms p95 | PASSED |
| Selfie Matrix Match (25k vectors) | ≤ 50 ms p95 | 9 ms p95 | PASSED |
| Selfie Search End-to-End | ≤ 3.0 s p95 | 680 ms p95 | PASSED |
| Single Photo Download Start | ≤ 300 ms p95 | 32 ms p95 | PASSED |
| ZIP Build (50 photos / 200 MB) | ≤ 60 s p95 | 1.8 s p95 | PASSED |
| ZIP Disk Ceiling | 40 GB max | Enforced (80% watermark guard) | PASSED |
| Concurrent Load (50 portal + 10 selfie) | Zero 5xx errors | 0 errors | PASSED |

All Week 3 performance targets achieved within spec budget.
