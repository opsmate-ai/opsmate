import json
from functools import wraps
from opentelemetry import trace
import inspect
from typing import Callable, Optional, Sequence, List
from contextlib import asynccontextmanager
import os
from opentelemetry.sdk.trace.sampling import Sampler, SamplingResult, Decision
from opentelemetry.trace import Context, TraceState, SpanKind, Link
from opentelemetry.util.types import Attributes
from collections import OrderedDict
import structlog

logger = structlog.get_logger()
tracer = trace.get_tracer("opsmate")


@asynccontextmanager
async def start_as_current_span_async(tracer, *args, **kwargs):
    with tracer.start_as_current_span(*args, **kwargs) as span:
        yield span


def traceit(*args, name: str = None, exclude: list = []):
    """
    Decorator to trace function calls.

    Usage:

    @traceit # all arguments will be traced as attributes
    def my_function(a, b, c):
        pass

    @traceit(exclude=["b"]) # b will not be traced as an attribute
    def my_function(a, b, c):
        pass


    @traceit # Span can be accessed in the function
    def my_function(a, b, c, span: Span = None):
        span.add_event("my_event", {"key": "value"})
        return a + b + c
    """
    if len(args) == 1 and callable(args[0]):
        return _traceit(args[0], name, exclude)
    elif len(args) == 0:

        def decorator(func: Callable):
            return _traceit(func, name, exclude)

        return decorator
    else:
        raise ValueError("Invalid arguments")


def _traceit(func: Callable, name: str = None, exclude: list = []):
    def _extract_params(args, kwargs):
        """
        Extract the parameters from the func, and return the parameters and Otel compatible attributes
        """
        kvs = {}
        parameters = inspect.signature(func).parameters
        parameter_items = list(parameters.values())
        for idx, val in enumerate(args):
            if parameter_items[idx].name in exclude:
                continue
            if parameter_items[idx].annotation in (int, str, bool, float):
                kvs[parameter_items[idx].name] = val
            elif parameter_items[idx].annotation in (dict, list):
                kvs[parameter_items[idx].name] = json.dumps(val)

        for k, v in kwargs.items():
            if k in exclude:
                continue
            if isinstance(k, (int, str, bool, float)):
                kvs[k] = v
            elif isinstance(k, (dict, list)):
                kvs[k] = json.dumps(v)

        return parameters, kvs

    @wraps(func)
    def wrapper(*args, **kwargs):
        parameters, kvs = _extract_params(args, kwargs)
        span_name = name or func.__qualname__
        with tracer.start_as_current_span(span_name) as span:
            for k, v in kvs.items():
                span.set_attribute(f"{span_name}.{k}", v)

            if parameters.get("span") is not None:
                kwargs["span"] = span

            return func(*args, **kwargs)

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        parameters, kvs = _extract_params(args, kwargs)
        span_name = name or func.__qualname__
        async with start_as_current_span_async(tracer, span_name) as span:
            for k, v in kvs.items():
                span.set_attribute(f"{span_name}.{k}", v)

            if parameters.get("span") is not None:
                kwargs["span"] = span

            return await func(*args, **kwargs)

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return wrapper


class DiscardSampler(Sampler):
    def __init__(self, spans_to_discard: List[str] = [], max_trace_ids: int = 1000):
        self.spans_to_discard = spans_to_discard
        self.max_trace_ids = max_trace_ids
        self.discarded_trace_ids = OrderedDict()

    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Attributes = None,
        links: Optional[Sequence[Link]] = None,
        trace_state: Optional[TraceState] = None,
    ) -> SamplingResult:
        if trace_id in self.discarded_trace_ids:
            self.discarded_trace_ids.move_to_end(trace_id)
            self.discarded_trace_ids[trace_id] = True
            return SamplingResult(
                decision=Decision.DROP, attributes=attributes, trace_state=trace_state
            )

        if name in self.spans_to_discard:
            if len(self.discarded_trace_ids) >= self.max_trace_ids:
                self.discarded_trace_ids.popitem(last=False)  # Remove oldest item

            self.discarded_trace_ids[trace_id] = True
            return SamplingResult(
                decision=Decision.DROP, attributes=attributes, trace_state=trace_state
            )

        return SamplingResult(
            decision=Decision.RECORD_AND_SAMPLE,
            attributes=attributes,
            trace_state=trace_state,
        )

    def get_description(self) -> str:
        return "Discard specific spans and their related traces with bounded memory"


def start_trace(spans_to_discard: List[str] = []):
    if os.getenv("OPSMATE_DISABLE_OTEL"):
        logger.info("OTEL is disabled")
        return

    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        from opentelemetry.instrumentation.openai import OpenAIInstrumentor
        from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
        )

        if os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL") == "grpc":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
        else:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

        from opentelemetry.sdk.resources import SERVICE_NAME, PROCESS_PID, Resource

        resource = Resource(
            attributes={
                SERVICE_NAME: os.getenv("SERVICE_NAME", "opsmate"),
                PROCESS_PID: os.getpid(),
            }
        )
        provider = TracerProvider(
            resource=resource,
            sampler=DiscardSampler(spans_to_discard=spans_to_discard),
        )
        exporter = OTLPSpanExporter()
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        OpenAIInstrumentor().instrument()
        AnthropicInstrumentor().instrument()
