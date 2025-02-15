from opsmate.ingestions import GithubIngestion
from opsmate.knowledgestore.models import init_table, aconn
from opsmate.ingestions.base import Document
from opsmate.libs.config import config
import structlog
from sqlmodel import create_engine, Session
from opsmate.dbq.dbq import enqueue_task, Worker, SQLModel
from typing import Dict, Any
import asyncio
import uuid
import json

logger = structlog.get_logger()

engine = create_engine(config.db_url, connect_args={"check_same_thread": False})


async def chunk_and_store(
    repo: str = "",
    glob: str = "",
    branch: str = "",
    doc: Dict[str, Any] = {},
):
    doc = Document(**doc)
    ingestion = GithubIngestion(repo=repo, glob=glob, branch=branch)
    db_conn = await aconn()
    table = await db_conn.open_table("knowledge_store")

    kbs = []
    async for chunk in ingestion.chunking_document(doc):
        kbs.append(
            {
                "uuid": str(uuid.uuid4()),
                "id": chunk.id,
                # "summary": chunk.metadata["summary"],
                "data_source_provider": chunk.metadata["data_source_provider"],
                "data_source": chunk.metadata["data_source"],
                "path": chunk.metadata["path"],
                "categories": [],
                "metadata": json.dumps(chunk.metadata),
                "content": chunk.content,
            }
        )

    # await table.add(kbs)
    await (
        table.merge_insert(["data_source_provider", "data_source", "path", "id"])
        .when_matched_update_all()
        .when_not_matched_insert_all()
        .when_not_matched_by_source_delete()
        .execute(kbs)
    )

    logger.info("chunks stored", repo=repo, glob=glob, branch=branch, num_kbs=len(kbs))


async def github_ingestion(repo: str, glob: str, branch: str):
    with Session(engine) as session:
        ingestion = GithubIngestion(repo=repo, glob=glob, branch=branch)

        async for doc in ingestion.load():
            logger.info(
                "github ingestion", repo=repo, glob=glob, branch=branch, doc=doc
            )
            enqueue_task(
                session,
                chunk_and_store,
                repo=repo,
                glob=glob,
                branch=branch,
                doc=doc.model_dump(),
            )


async def main():
    SQLModel.metadata.create_all(engine)
    await init_table()

    worker = Worker(Session(engine), concurrency=10)
    worker_task = asyncio.create_task(worker.start())

    await github_ingestion(repo="jingkaihe/opsmate", glob="**/*.md", branch="main")

    await worker_task


if __name__ == "__main__":
    asyncio.run(main())
