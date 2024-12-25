import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from opsmate.libs.core.trace import traceit


@pytest.fixture(scope="module", autouse=True)
def tracer_provider():
    exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    span_processor = SimpleSpanProcessor(exporter)
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)
    yield tracer_provider, exporter

    # teardown
    tracer_provider.shutdown()
    exporter.clear()
    span_processor.shutdown()


def test_traceit_with_args(tracer_provider):
    tracer_provider, exporter = tracer_provider

    @traceit
    def func(a: int, b: str, c: dict):
        return a + len(b) + len(c)

    result = func(1, "world", {"y": 2})

    assert result == 7

    spans = exporter.get_finished_spans()
    span = spans[-1]
    assert span.name == "test_traceit_with_args.<locals>.func"
    assert span.attributes["test_traceit_with_args.<locals>.func.a"] == 1
    assert span.attributes["test_traceit_with_args.<locals>.func.b"] == "world"
    assert span.attributes["test_traceit_with_args.<locals>.func.c"] == '{"y": 2}'


def test_traceit_with_name(tracer_provider):
    tracer_provider, exporter = tracer_provider

    @traceit(name="da_func")
    def func(a: int, b: str, c: dict):
        return a + len(b) + len(c)

    result = func(1, "world", {"y": 2})

    assert result == 7

    spans = exporter.get_finished_spans()
    span = spans[-1]
    assert span.name == "da_func"
    assert span.attributes["da_func.a"] == 1
    assert span.attributes["da_func.b"] == "world"
    assert span.attributes["da_func.c"] == '{"y": 2}'


def test_traceit_with_exclude(tracer_provider):
    tracer_provider, exporter = tracer_provider

    @traceit(name="da_func", exclude=["b"])
    def func(a: int, b: str, c: dict):
        return a + len(b) + len(c)

    result = func(1, "hello", {"x": 1})

    assert result == 7

    spans = exporter.get_finished_spans()
    span = spans[-1]

    assert span.name == "da_func"
    assert span.attributes["da_func.a"] == 1
    assert span.attributes["da_func.c"] == '{"x": 1}'
    assert "da_func.b" not in span.attributes


def test_traceit_with_span_arg(tracer_provider):
    tracer_provider, exporter = tracer_provider

    @traceit(name="da_func")
    def func(a: int, span: trace.Span = None):
        span.add_event("test_event")
        return a

    result = func(1)
    assert result == 1

    spans = exporter.get_finished_spans()
    span = spans[-1]
    assert span.name == "da_func"
    assert span.attributes["da_func.a"] == 1
    assert span.events[0].name == "test_event"


@pytest.mark.asyncio
async def test_async_traceit_with_args(tracer_provider):
    tracer_provider, exporter = tracer_provider

    @traceit
    async def func(a: int, b: str, c: dict):
        return a + len(b) + len(c)

    result = await func(1, "world", {"y": 2})

    assert result == 7

    spans = exporter.get_finished_spans()
    span = spans[-1]
    assert span.name == "test_async_traceit_with_args.<locals>.func"
    assert span.attributes["test_async_traceit_with_args.<locals>.func.a"] == 1
    assert span.attributes["test_async_traceit_with_args.<locals>.func.b"] == "world"
    assert span.attributes["test_async_traceit_with_args.<locals>.func.c"] == '{"y": 2}'


@pytest.mark.asyncio
async def test_async_traceit_with_name(tracer_provider):
    tracer_provider, exporter = tracer_provider

    @traceit(name="da_func")
    async def func(a: int, b: str, c: dict):
        return a + len(b) + len(c)

    result = await func(1, "world", {"y": 2})

    assert result == 7

    spans = exporter.get_finished_spans()
    span = spans[-1]
    assert span.name == "da_func"
    assert span.attributes["da_func.a"] == 1
    assert span.attributes["da_func.b"] == "world"
    assert span.attributes["da_func.c"] == '{"y": 2}'


@pytest.mark.asyncio
async def test_async_traceit_with_exclude(tracer_provider):
    tracer_provider, exporter = tracer_provider

    @traceit(name="da_func", exclude=["b"])
    async def func(a: int, b: str, c: dict):
        return a + len(b) + len(c)

    result = await func(1, "hello", {"x": 1})
    assert result == 7

    spans = exporter.get_finished_spans()
    span = spans[-1]
    assert span.name == "da_func"
    assert span.attributes["da_func.a"] == 1
    assert span.attributes["da_func.c"] == '{"x": 1}'
    assert "da_func.b" not in span.attributes


@pytest.mark.asyncio
async def test_async_traceit_with_span_arg(tracer_provider):
    tracer_provider, exporter = tracer_provider

    @traceit(name="da_func")
    async def func(a: int, span: trace.Span = None):
        span.add_event("test_event")
        return a

    result = await func(1)
    assert result == 1

    spans = exporter.get_finished_spans()
    span = spans[-1]
    assert span.name == "da_func"
    assert span.attributes["da_func.a"] == 1

    assert span.events[0].name == "test_event"
