import pytest
from opsmate.tests.base import BaseTestCase
from opsmate.ingestions.fs import FsIngestion
from opsmate.textsplitters.markdown_header import MarkdownHeaderTextSplitter
from opsmate.ingestions.chunk import chunk_document
from os import path


class TestFsIngestion(BaseTestCase):
    @pytest.fixture
    def fixtures_dir(self):
        current_dir = path.dirname(path.abspath(__file__))
        return path.join(current_dir, "fixtures")

    @pytest.mark.asyncio
    async def test_ingestion_load(self, fixtures_dir):
        ingestion = FsIngestion(
            local_path=fixtures_dir,
            glob_pattern="**/*.md",
        )

        docs = [doc async for doc in ingestion.load()]

        def find_doc(name: str):
            for doc in docs:
                if doc.metadata["name"] == name:
                    return doc
            assert False, f"Document with name {name} not found"

        doc = find_doc("TEST.md")
        assert doc.metadata["name"] == "TEST.md"
        assert doc.metadata["path"].endswith("/TEST.md")

        doc = find_doc("TEST2.md")
        assert doc.metadata["name"] == "TEST2.md"
        assert doc.metadata["path"].endswith("/nested/TEST2.md")

    @pytest.mark.asyncio
    async def test_ingestion_ingest(self, fixtures_dir):
        ingestion = FsIngestion(
            local_path=fixtures_dir,
            glob_pattern="**/*.md",
        )

        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
            ]
        )

        chunks = []
        async for doc in ingestion.load():
            async for chunk in chunk_document(splitter=splitter, document=doc):
                chunks.append(chunk)

        assert len(chunks) == 6
        # print(chunks)
        assert "h1" in chunks[0].metadata
        assert (
            chunks[0].content == "This document is used to test the document ingestion."
        )
        assert chunks[0].metadata["path"].endswith("/TEST.md")

        assert "h1" in chunks[1].metadata
        assert "h2" in chunks[1].metadata
        assert chunks[1].content == "Hello this is test 1"
        assert chunks[1].metadata["path"].endswith("/TEST.md")

        assert "h1" in chunks[2].metadata
        assert "h2" in chunks[2].metadata
        assert "Hello this is test 2, here is some code:" in chunks[2].content
        assert chunks[2].metadata["path"].endswith("/TEST.md")

        assert "h1" in chunks[3].metadata
        assert "h2" in chunks[3].metadata
        assert "h3" in chunks[3].metadata
        assert "go run main.go" in chunks[3].content
        assert chunks[3].metadata["path"].endswith("/TEST.md")

        assert "h1" in chunks[4].metadata
        assert "h2" in chunks[4].metadata
        assert "nginx-service" in chunks[4].content
        assert chunks[4].metadata["path"].endswith("/TEST.md")

        assert "h1" in chunks[5].metadata
        assert "This is a test 2" in chunks[5].content
        assert chunks[5].metadata["path"].endswith("/nested/TEST2.md")

    def test_from_config(self):
        config = {
            "/tmp/foo": "*.md",
            "/tmp/bar": "*.txt",
        }
        ingestions = FsIngestion.from_configmap(config)
        assert len(ingestions) == 2
        assert ingestions[0].local_path == "/tmp/foo"
        assert ingestions[0].glob_pattern == "*.md"
        assert ingestions[1].local_path == "/tmp/bar"
        assert ingestions[1].glob_pattern == "*.txt"
