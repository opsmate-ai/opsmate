[Grafana Loki](https://grafana.com/oss/loki/) is a horizontally scalable, highly available, multi-tenant log aggregation system inspired by Prometheus. It is designed to be very cost effective and easy to operate. It does not index the contents of the logs, but rather a set of labels for each log stream.

Opsmate offers `LokiQueryTool` to query logs in loki via natural language.

:warning: This is a highly experimental tool and the API is subject to change.
## Prerequisites

* You have your system logs pushed to loki
* You have access to the loki api

## Setup

`LokiQueryTool` is out of box supported by Opsmate without plugin installation.

Here are the default configuration for the tool:

```bash
LOKI_ENDPOINT=http://localhost:3100
LOKI_PATH=/api/v1/query_range
# Optional: LOKI_USER_ID
# Optional: LOKI_API_KEY
```

You can also override the default configuration by setting the environment variables. In the example below we point Opsmate to a loki instance deployed within the Grafana Cloud:

```bash
LOKI_ENDPOINT=https://logs-prod-eu-west-0.grafana.net/loki
LOKI_USER_ID=xxxx
LOKI_API_KEY=glc_xxx
```

To use the tool you can specify `LokiQueryTool` as part of the `--tools` option when running `opsmate run`, `opsmate solve`, `opsmate chat` or `opsmate serve`:

```bash
opsmate run --tools LokiQueryTool,OtherTool ...
```

Alternatively you can add the tool in `~/.opsmate/config.yaml` via:

```yaml
OPSMATE_TOOLS:
- LokiQueryTool
- OtherTool
```

Once the tool is added to the config, Opsmate will prioritise using Loki for query logs over other tools.

## Current Limitations

* The Loki Tool at the moment is Kubernetes centric meaning it can only query based on the `namespace`, `pod` and `container` labels.
* The tool at the moment only support `logfmt` and `json` for effective log parsing.
