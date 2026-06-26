# QueueStorm Investigator Runbook

## Local

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8000/metrics
```

## Compose

```bash
docker compose up --build
```

## Kubernetes

Create secrets first:

```bash
kubectl create namespace queuestorm
kubectl -n queuestorm create secret generic queuestorm-secrets \
  --from-literal=auth-jwt-secret='replace-me' \
  --from-literal=anthropic-api-key=''
kubectl apply -f deploy/k8s/
```

## Failure Checks

- `/ready` should be `ok` unless a required dependency is unavailable.
- `/metrics` should expose request counters and average latency.
- `/observability/traces` should show recent request paths and correlation IDs.
- Check `/events/dead-letter` for failed async processing.
