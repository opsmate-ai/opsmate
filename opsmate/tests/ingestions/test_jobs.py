import pytest
from sqlmodel import create_engine, Session
from opsmate.dbq.dbq import Worker, SQLModel as DBQSQLModel, enqueue_task
from opsmate.ingestions.models import SQLModel as IngestionSQLModel, IngestionRecord
import asyncio
from contextlib import asynccontextmanager
import structlog
from sqlalchemy import Engine
from opsmate.ingestions.jobs import ingest
import time
from opsmate.knowledgestore.models import aconn
from opsmate.tests.base import BaseTestCase
from opsmate.ingestions.fs import FsIngestion
from opsmate.ingestions.jobs import ingestor_from_config
import os

logger = structlog.get_logger(__name__)


class TestJobs(BaseTestCase):
    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        IngestionSQLModel.metadata.create_all(engine)
        DBQSQLModel.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine: Engine):
        with Session(engine) as session:
            yield session

    @asynccontextmanager
    async def with_worker(self, engine: Engine):
        worker = Worker(engine, concurrency=5)
        worker_task = asyncio.create_task(worker.start())
        try:
            yield worker
        finally:
            await worker.stop()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                logger.info("worker task cancelled")

    @pytest.mark.skipif(
        os.getenv("CI") == "true", reason="flakey test on Github Actions"
    )
    @pytest.mark.asyncio
    async def test_ingest(self, engine: Engine, session: Session):
        async def ingest_all():
            enqueue_task(
                session,
                ingest,
                ingestor_type="fs",
                ingestor_config={
                    "local_path": ".",
                    "glob_pattern": "./README.md",
                },
            )

        async def get_kbs():
            return (
                await table.query()
                .where("data_source_provider = 'fs'")
                .select(
                    ["id", "data_source_provider", "data_source", "path", "categories"]
                )
                .to_list()
            )

        async with self.with_worker(engine) as worker:
            await ingest_all()
            await self.await_task_pool_idle(worker)

            conn = await aconn()
            table = await conn.open_table("knowledge_store")
            kbs = await get_kbs()
            current_kbs_len = len(kbs)

            categories = [kb["categories"] for kb in kbs]
            ids = [kb["id"] for kb in kbs]
            data_sources = [kb["data_source"] for kb in kbs]
            data_source_providers = [kb["data_source_provider"] for kb in kbs]
            paths = [kb["path"] for kb in kbs]

            # assert the ingestion record was created
            ingestion_record = await IngestionRecord.find_or_create(
                session, "fs", {"local_path": ".", "glob_pattern": "./README.md"}
            )

            assert ingestion_record is not None, "Should have an ingestion record"
            assert len(ingestion_record.documents) > 0, "Should have documents"

            assert current_kbs_len > 0, "Should have at least one kb"
            assert all(
                len(c) > 0 for c in categories
            ), "All categories should be non-empty"
            assert all(id is not None for id in ids), "All ids should be non-None"
            assert all(
                data_source_provider == "fs"
                for data_source_provider in data_source_providers
            ), "All data source providers should be fs"
            assert all(
                path.startswith("/") for path in paths
            ), "All paths should be absolute"
            assert all(
                data_source in ["README.md", "docs/**/*.md"]
                for data_source in data_sources
            ), "All data sources should be valid"

            # ingest again
            await ingest_all()
            await self.await_task_pool_idle(worker)

            kbs = await get_kbs()
            assert len(kbs) == current_kbs_len, "Should have the same number of kbs"

    async def await_task_pool_idle(self, worker: Worker, timeout: float = 10):
        start = time.time()
        while not worker.idle():
            await asyncio.sleep(0.1)
            if time.time() - start > timeout:
                raise TimeoutError("Task pool did not idle in time")
        return True

    @pytest.mark.asyncio
    async def test_ingest_from_config(self):
        config = {
            "local_path": ".",
            "glob_pattern": "./README.md",
        }

        ingestion = ingestor_from_config("fs", config)
        assert isinstance(ingestion, FsIngestion)
        assert ingestion.local_path == "."
        assert ingestion.glob_pattern == "./README.md"

        # config = {
        #     "repo": "opsmate/opsmate",
        #     "branch": "main",
        #     "path": "README.md",
        # }

        # ingestion = ingestor_from_config("github", config)
        # assert isinstance(ingestion, GithubIngestion)
        # assert ingestion.repo == "opsmate/opsmate"
        # assert ingestion.branch == "main"
        # assert ingestion.path == "README.md"
