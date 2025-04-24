PrometheusTool is a tool to query metrics from prometheus tsdb via natural language. The tool itself is out of box supported by opsmate and added to all the prebuilt contexts.

You can also explicitly add the tool to your session via

```bash
opsmate [run|solve|chat|serve] --models PrometheusTool ...
```

You can configure the prometheus endpoint and other parameters via environment variables:

```bash
PROMETHEUS_ENDPOINT=http://localhost:9090 # default endpoint
PROMETHEUS_PATH=/api/v1/query # default path
# Optional: PROMETHEUS_USER_ID
# Optional: PROMETHEUS_API_KEY
```

Example usage:

Here is a simple example of how to use the tool (you probably need to zoom in to see the text):

<script
  src="https://asciinema.org/a/715257.js"
  id="asciicast-715257"
  async="true"
  data-theme="solarized-dark"
  data-speed="2"
  data-loop=true
  data-autoplay=true
  data-rows="60"
></script>

Note that for LLM to come up with the correct promql query, you need to provide enough information about:

- the metrics name
- the labels

In Opsmate you can store the metrics metadata in the vector db and ask LLM to retrieve the metrics semantically on the fly.

See [ingest-prometheus-metrics-metadata](../CLI/ingest-prometheus-metrics-metadata.md) for more details.
