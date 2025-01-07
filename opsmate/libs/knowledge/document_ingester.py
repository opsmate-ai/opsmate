from opentelemetry import trace
from pydantic import BaseModel, Field
from typing import Dict
from .schema import get_runbooks_table
from lancedb.table import Table
from opsmate.textsplitters.markdown_header import MarkdownHeaderTextSplitter
from opsmate.textsplitters.base import Chunk
import glob
import structlog
import uuid

logger = structlog.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class Metadata(BaseModel):
    name: str = Field(title="name")
    namespace: str = Field(title="namespace", default="default")
    labels: Dict[str, str] = Field(title="labels", default={})
    description: str = Field(title="description", default="")


class DocumentIngestionSpec(BaseModel):
    local_path: str = Field(
        title="local path",
        description="absolute path to the directory to ingest, glob patterns are supported",
    )


class DocumentIngestion(BaseModel):
    metadata: Metadata = Field(title="metadata")
    spec: DocumentIngestionSpec = Field(title="spec")


class DocumentIngester:
    def __init__(self, table: Table = None):
        if table is None:
            self.runbooks_table = get_runbooks_table()
        else:
            self.runbooks_table = table

        self.text_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "heading 1"),
                ("##", "heading 2"),
                ("###", "heading 3"),
            ]
        )

    def document_ingestion(self, ingestion: DocumentIngestion, batch_size: int = 100):
        """
        Ingest the documents into the backend storage.

        Args:
            ingestion: The document ingestion object.

        Yields:
            The documents.
        """

        batch = []

        with tracer.start_as_current_span("document_ingestion") as span:
            for file in self.document_discovery(ingestion):
                for doc in self.split_text(file):
                    batch.append(
                        {
                            "uuid": str(uuid.uuid4()),
                            "filename": file,
                            "heading": self.chunk_header(doc),
                            "content": self.chunk_content(doc),
                        }
                    )

                    if len(batch) == batch_size:
                        logger.info("batch ingest runbooks", batch_size=batch_size)
                        span.add_event("ingesting_batch", {"batch_size": batch_size})
                        self.runbooks_table.add(batch)
                        batch = []

            if len(batch) > 0:
                logger.info("batch ingest runbooks", batch_size=len(batch))
                span.add_event("ingesting_batch", {"batch_size": len(batch)})
                self.runbooks_table.add(batch)

    def document_discovery(self, ingestion: DocumentIngestion):
        """
        Discover the documents from the local path and yield the document chunks.

        Args:
            ingestion: The document ingestion object.

        Yields:
            The documents.
        """

        with tracer.start_as_current_span("document_discovery") as span:
            span.set_attributes(
                {
                    "document_discovery.name": ingestion.metadata.name,
                    "document_discovery.namespace": ingestion.metadata.namespace,
                    "document_discovery.local_path": ingestion.spec.local_path,
                }
            )

            # find all the files in the local path
            files = glob.glob(ingestion.spec.local_path)

            span.set_attribute("document_discovery.files_count", len(files))
            for file in files:
                yield file

    def split_text(self, filename: str):
        with tracer.start_as_current_span("split_text") as span:
            span.set_attribute("filename", filename)

            with open(filename, "r") as f:
                content = f.read()
                docs = self.text_splitter.split_text(text=content)

                count = 0
                for doc in docs:
                    count += 1
                    yield doc

                span.set_attribute("split_text.docs_count", count)

    def chunk_content(self, document: Chunk):
        content = ""
        if document.metadata.get("heading 1"):
            content += document.metadata.get("heading 1")
        if document.metadata.get("heading 2"):
            content += document.metadata.get("heading 2")
        if document.metadata.get("heading 3"):
            content += document.metadata.get("heading 3")

        content += document.content

        return content

    def chunk_header(self, document: Chunk):
        if document.metadata.get("heading 3"):
            return document.metadata.get("heading 3")
        elif document.metadata.get("heading 2"):
            return document.metadata.get("heading 2")
        elif document.metadata.get("heading 1"):
            return document.metadata.get("heading 1")
        return ""
