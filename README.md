# Lab 4: Monitoring & Production Deployment

Comprehensive monitoring and observability for the movie rating prediction system: **Prometheus** metrics collection, **Grafana** dashboards, **12 alerting rules**, and load testing. All 10 metrics implemented (10/10 shown at the root endpoint).

## Project Structure

```
ddm501-lab4/
├── app/
│   ├── main.py             # FastAPI app + /metrics endpoint
│   ├── model.py            # ML model with full metrics instrumentation
│   ├── metrics.py          # 10 Prometheus metrics (Counter/Histogram/Gauge/Info)
│   ├── middleware.py       # HTTP metrics middleware
│   ├── schemas.py          # Pydantic schemas
│   └── config.py
├── prometheus/
│   ├── prometheus.yml      # Scrape config: api:8000/metrics @10s + node-exporter
│   └── alerts/
│       ├── api_alerts.yml  # 5 API alerts
│       └── ml_alerts.yml   # 7 ML alerts
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/prometheus.yml   # Auto-configured Prometheus (uid: prometheus)
│   │   └── dashboards/dashboards.yml    # Auto-load dashboards
│   └── dashboards/
│       ├── system_dashboard.json        # 5 panels (rate, latency, errors, status, endpoints)
│       └── ml_dashboard.json            # 9 panels (model status, predictions, latency, drift)
├── scripts/
│   ├── train_model.py
│   └── load_test.py        # Standard + variable-load + spike test modes
├── tests/test_metrics.py   # 15 tests
├── docker-compose.yml      # api + prometheus + grafana + node-exporter
├── Dockerfile
└── requirements.txt
```

## Quick Start

```bash
# 1. Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Train model
python scripts/train_model.py

# 3. Start the full monitoring stack
docker-compose up -d

# 4. Generate traffic so dashboards have data
python scripts/load_test.py --duration 120 --workers 10
```

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | — |
| API Docs | http://localhost:8000/docs | — |
| Raw metrics | http://localhost:8000/metrics | — |
| Prometheus | http://localhost:9090 | — |
| Prometheus alerts | http://localhost:9090/alerts | — |
| Grafana | http://localhost:3000 | admin / admin |
| Node Exporter | http://localhost:9100/metrics | — |

Both dashboards are **auto-provisioned** — open Grafana → Dashboards and they're already there with the Prometheus datasource wired up.

## Implemented Metrics (10/10)

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `http_requests_total` | Counter | method, endpoint, status | Traffic + error rate |
| `http_request_duration_seconds` | Histogram | method, endpoint | HTTP latency (P50/P95/P99) |
| `ml_predictions_total` | Counter | model_version | Prediction volume |
| `ml_prediction_duration_seconds` | Histogram | model_version | Model inference latency |
| `ml_prediction_value` | Histogram | model_version | Rating distribution (drift signal) |
| `ml_prediction_errors_total` | Counter | error_type, model_version | Failure tracking |
| `ml_model_loaded` | Gauge | — | Model health (1/0) |
| `ml_model_info` | Info | version, type, path | Model metadata |
| `ml_model_last_reload_timestamp` | Gauge | — | Staleness detection |
| `ml_batch_prediction_size` | Histogram | — | Batch size distribution (bonus) |

## Alert Rules (12 total)

**API alerts** (`prometheus/alerts/api_alerts.yml`): HighErrorRate (>10% 5xx, critical), HighLatency (P95 >1s, warning), ServiceDown (critical), HighRequestRate (>1000 req/s, bonus), LowRequestRate (bonus).

**ML alerts** (`prometheus/alerts/ml_alerts.yml`): ModelNotLoaded (critical), PredictionLatencyHigh (P95 >100ms), LowPredictionVolume, PredictionDistributionAnomaly (median shift >0.5 vs 24h ago — simple drift detection), HighPredictionErrorRate (>5%, critical), ModelStale (>7 days, bonus), ExtremePredictionsHigh (>30% at extremes, bonus).

View them under Prometheus → Alerts. To test ModelNotLoaded: `docker-compose exec api rm /app/models/svd_model.pkl` then restart the api container.

## Load Testing

```bash
python scripts/load_test.py                            # 60s, 10 workers
python scripts/load_test.py --duration 120 --workers 20
python scripts/load_test.py --batch                    # batch predictions
python scripts/load_test.py --variable --duration 120 --workers 50   # ramp up/sustain/down
python scripts/load_test.py --spike --workers 5        # normal -> 100-worker spike -> normal
```

Prints total/success/RPS plus min/max/mean/median/stddev and P50/P95/P99 latencies.

## Verification Checklist (for screenshots)

1. `curl localhost:8000/` shows `"metrics_implemented": "10/10"`.
2. Run the load test, then in Grafana: System dashboard shows request rate climbing, latency percentiles, status pie chart; ML dashboard shows Model Status = Loaded (green), prediction rate, latency P50/P95/P99, and rating distribution across 1–5.
3. Prometheus → Status → Targets: `movie-rating-api` and `node` both UP.
4. Prometheus → Alerts: 12 rules loaded, all green when healthy.

## Useful PromQL

```promql
rate(http_requests_total[5m])
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
rate(ml_predictions_total[5m])
histogram_quantile(0.5, sum(rate(ml_prediction_value_bucket[5m])) by (le))
```

## Running Tests

```bash
pytest tests/ -v        # 15 tests covering metric definitions, labels, /metrics endpoint
```
