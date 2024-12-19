from opsmate.libs.core.types import DocumentIngestion, DocumentIngestionSpec, Metadata
from opsmate.libs.knowledge import DocumentIngester, get_runbooks_table, Runbook
import os
import structlog
from opsmate.tests.base import BaseTestCase

logger = structlog.get_logger()


class TestIngestions(BaseTestCase):
    def test_document_discovery(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(current_dir, "fixtures/*.md")

        ingestion = DocumentIngestion(
            metadata=Metadata(name="test"),
            spec=DocumentIngestionSpec(local_path=full_path),
        )

        ingester = DocumentIngester()
        docs = []
        for doc in ingester.document_discovery(ingestion):
            for d in ingester.split_text(doc):
                docs.append(d)

        assert len(docs) == 5
        assert "heading 1" in docs[0].metadata
        assert (
            docs[0].page_content
            == "This document is used to test the document ingestion."
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

    def test_document_ingestion(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(current_dir, "fixtures/*.md")

        ingestion = DocumentIngestion(
            metadata=Metadata(name="test"),
            spec=DocumentIngestionSpec(local_path=full_path),
        )

        ingester = DocumentIngester()
        ingester.document_ingestion(ingestion)

        runbooks = (
            get_runbooks_table().search("kubernetes").limit(1).to_pydantic(Runbook)
        )
        assert len(runbooks) == 1

        assert runbooks[0].filename.endswith("fixtures/TEST.md")
        assert "test 3" in runbooks[0].heading
        assert "nginx-service" in runbooks[0].content
