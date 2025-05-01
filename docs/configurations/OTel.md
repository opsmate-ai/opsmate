Opsmate provides built-in integration with [OpenTelemetry](https://opentelemetry.io/) for distributed tracing. This allows you to monitor and troubleshoot your application's performance and behavior.

## Setup

To enable OTel tracing, set the following environment variables:

```bash
# Required: OTLP endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=http://your-collector:4317

# Optional: Protocol - defaults to HTTP if not specified
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc  # or "http"

# Optional: Service name - defaults to "opsmate"
export SERVICE_NAME=<your-service-name>

# Optional: OTel header - typically for the purpose of breaer or basic auth
export OTEL_EXPORTER_OTEL_HEADER=
```

Here is the official documentation for the OTel configuration:

- [OTLP Exporter](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/)


After setting up, the following commands are OTel traced:

- [opsmate run](../CLI/run.md)
- [opsmate solve](../CLI/solve.md)
- [opsmate chat](../CLI/chat.md)
- [opsmate serve](../CLI/serve.md)
- [opsmate worker](../CLI/worker.md)

## Automatic Instrumentation

Out of the box, the following integrations are automatically instrumented:

- OpenAI API and OpenAI compatible providers API calls
- Anthropic API calls
- SQLAlchemy database calls (when the database operations are performed)
- Starlette HTTP requests (when running in server mode)

## Disable Tracing

To disable tracing, set the following environment variable:

```bash
export OPSMATE_DISABLE_OTEL=true

# or

unset OTEL_EXPORTER_OTLP_ENDPOINT
```
