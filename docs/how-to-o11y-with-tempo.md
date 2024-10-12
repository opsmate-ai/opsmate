# How to setup observability with Tempo

To run Grafana and Tempo locally:

```bash
(
  cd tempo
  docker compose up -d
)
```

To run OpsMate with tracing enabled:

```bash
OTEL_ENABLED=true opsmate chat
```
