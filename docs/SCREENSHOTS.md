# Grafana & Prometheus Screenshots — Lab 4

Submission evidence for "Load Test Results: Screenshots showing metrics during load test" (assignment §5.3).

All screenshots captured 2026-08-09 from the live Docker monitoring stack (api, prometheus, grafana, node-exporter) during/after a 120s × 20-worker load test (18300 requests, 100% success, P95 25.51 ms — see `load_test_results.txt`).

## Screenshots

| File | Source | What it shows |
|---|---|---|
| `screenshots/image_16eb93.png` | Grafana — ML Metrics Dashboard (`/d/ml-metrics`) | Model Status: Loaded (SVD, v1.0.0); Prediction Rate ~63 ops/s with spike from ~11:55; Prediction Latency P99 ~1 ms; Prediction Median 3.36; Prediction Error Rate 0% |
| `screenshots/image_16eb34.png` | Grafana — System Metrics Dashboard (`/d/system-metrics`) | Request Rate spike ~60 req/s (mostly POST /predict); Request Latency P99 45–50 ms, P95 35–40 ms, P50 <10 ms |
| `screenshots/image_16eaf9.png` | Grafana — System Metrics Dashboard (status) | Status Code Distribution 100% 200; Error Rate (5xx) 0% |
| `screenshots/image_16ead8.png` | Prometheus — `/targets` | 3 targets UP: movie-rating-api, node (node-exporter), prometheus |
| `screenshots/image_16eab4.png` | Prometheus — `/alerts` | 12 alert rules loaded (7 ML + 5 API), 0 firing (all inactive/healthy) |

## Rubric mapping

- **Dashboards & Alerts (30%)** — 2 dashboards (ML 9 panels + System 5 panels) + 12 alert rules, evidenced live.
- **Documentation (20%)** — load test report = these screenshots + `load_test_results.txt`.

## Notes

- Model latency (P99 ~1 ms, `ml_prediction_duration_seconds`) is the in-process `model.predict()` time; HTTP end-to-end latency (P95 25.51 ms, P99 42.49 ms from load test) includes network + middleware. Both correct — model inference << HTTP round-trip.
- 0 firing alerts under load confirms alert thresholds are sensible (no false positives at 152 req/s).