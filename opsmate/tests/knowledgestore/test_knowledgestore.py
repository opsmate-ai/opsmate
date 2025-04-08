import pytest
import asyncio
import uuid
from datetime import datetime, UTC

from opsmate.tests.base import BaseTestCase
from opsmate.knowledgestore.models import (
    Category,
    OpenAIEmbeddingClient,
    SentenceTransformersEmbeddingClient,
    get_embedding_client,
    get_reranker,
    aconn,
    conn,
    init_table,
    reindex_table,
    schedule_reindex_table,
    ReindexTableTask,
)
from opsmate.config import config
from opsmate.dbq.dbq import SQLModel, TaskItem, TaskStatus
from sqlmodel import Session, select


class TestKnowledgeStore(BaseTestCase):
    @pytest.fixture
    def session(self):
        config.db_url = "sqlite:///:memory:"
        engine = config.db_engine()
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    @pytest.mark.asyncio
    async def test_init_table(self):
        # Test creating and using a real LanceDB table
        table = await init_table()
        assert table is not None

        # Create a test record
        test_record = {
            "uuid": str(uuid.uuid4()),
            "id": 1,
            "categories": [Category.SECURITY.value],
            "data_source_provider": "test",
            "data_source": "test_source",
            "metadata": "{}",
            "path": "/test/path",
            "content": "Test content for embedding",
            "created_at": datetime.now(UTC),
        }

        # Add the record to the table
        await table.add([test_record])

        # Verify search works
        results = await table.query().select(["content"]).limit(5).to_arrow()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_connection_functions(self):
        # Test async connection
        async_db = await aconn()
        assert async_db is not None

        # Test sync connection
        sync_db = conn()
        assert sync_db is not None

        # Verify we can open the knowledge_store table
        table = await async_db.open_table("knowledge_store")
        assert table is not None

        sync_table = sync_db.open_table("knowledge_store")
        assert sync_table is not None

    @pytest.mark.asyncio
    async def test_embedding_client_configuration(self):
        # Test with the current configuration
        client = get_embedding_client()

        # Verify we got an embedding client that matches the current config
        if config.embedding_registry_name == "openai":
            assert isinstance(client, OpenAIEmbeddingClient)
        elif config.embedding_registry_name == "sentence-transformers":
            assert isinstance(client, SentenceTransformersEmbeddingClient)

    @pytest.mark.asyncio
    async def test_reranker_configuration(self):
        # Test the reranker based on current configuration
        reranker = get_reranker()

        # Verify reranker matches the configured type
        if config.reranker_name == "answerdotai":
            try:
                import transformers

                assert reranker.__class__.__name__ == "AnswerdotaiRerankers"
            except ImportError:
                assert reranker.__class__.__name__ == "OpenaiReranker"
        elif config.reranker_name == "openai":
            assert reranker.__class__.__name__ == "OpenaiReranker"
        elif config.reranker_name == "cohere":
            assert reranker.__class__.__name__ == "CohereReranker"
        elif config.reranker_name == "rrf":
            assert reranker.__class__.__name__ == "RRFReranker"
        else:
            assert reranker is None

    @pytest.mark.asyncio
    async def test_reindex_table(self):
        assert isinstance(reindex_table, ReindexTableTask)

    @pytest.mark.asyncio
    async def test_schedule_reindex_table(self, session):
        await schedule_reindex_table(session, interval_seconds=1)

        tasks = session.exec(
            select(TaskItem).where(
                TaskItem.func == "opsmate.knowledgestore.models.reindex_table"
            )
        ).all()
        assert len(tasks) == 1
        task = tasks[0]

        assert task.status == TaskStatus.PENDING
        assert task.kwargs == {"interval_seconds": 1}
        assert task.priority == 100
