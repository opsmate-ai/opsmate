from langchain_text_splitters import MarkdownHeaderTextSplitter
from opentelemetry import trace
from opsmate.libs.core.types import DocumentIngestion
import glob

tracer = trace.get_tracer(__name__)


class DocumentIngester:
    def __init__(self):
        self.text_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "heading 1"),
                ("##", "heading 2"),
                ("###", "heading 3"),
            ]
        )

    def document_ingestion(self, ingestion: DocumentIngestion):
        """
        Ingest the documents from the local path and yield the documents.

        Args:
            ingestion: The document ingestion object.
            span: The span object.

        Yields:
            The documents.
        """

        with tracer.start_as_current_span("document_ingestion") as span:
            span.set_attributes(
                {
                    "ingestion.name": ingestion.metadata.name,
                    "ingestion.namespace": ingestion.metadata.namespace,
                    "ingestion.local_path": ingestion.spec.local_path,
                }
            )

            # find all the files in the local path
            files = glob.glob(ingestion.spec.local_path)

            span.set_attribute("ingestion.files_count", len(files))
            for file in files:
                yield from self.split_text(file)

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
