from opsmate.libs.core.types import DocumentIngestion, DocumentIngestionSpec, Metadata
from opsmate.libs.ingestions import DocumentIngester
import os
import structlog
from opsmate.libs.core.trace import traceit
from opentelemetry.trace import Span
import opentelemetry.trace as trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

logger = structlog.get_logger()

resource = Resource(
    attributes={SERVICE_NAME: os.getenv("SERVICE_NAME", "opamate-eval")}
)

provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
    insecure=True,
)
processor = BatchSpanProcessor(exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)


@traceit(name="test_document_ingestion")
def test_document_ingestion(span: Span = None):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_dir, "fixtures/*.md")

    ingestion = DocumentIngestion(
        metadata=Metadata(name="test"),
        spec=DocumentIngestionSpec(local_path=full_path),
    )

    ingester = DocumentIngester()
    docs = [doc for doc in ingester.document_ingestion(ingestion)]

    assert len(docs) == 5
    assert "heading 1" in docs[0].metadata
    assert (
        docs[0].page_content == "This document is used to test the document ingestion."
    )

    assert "heading 1" in docs[1].metadata
    assert "heading 2" in docs[1].metadata
    assert docs[1].page_content == "Hello this is test 1"

    assert "heading 1" in docs[2].metadata
    assert "heading 2" in docs[2].metadata
    assert "Hello this is test 2, here is some code:" in docs[2].page_content

    assert "heading 1" in docs[3].metadata
    assert "heading 2" in docs[3].metadata
    assert "heading 3" in docs[3].metadata
    assert "go run main.go" in docs[3].page_content

    assert "heading 1" in docs[4].metadata
    assert "heading 2" in docs[4].metadata
    assert "nginx-service" in docs[4].page_content
