from opsmate.ingestions import GithubIngestion, FsIngestion
from opsmate.knowledgestore.models import init_table, aconn, Category
from opsmate.ingestions.base import Document
from opsmate.libs.config import config
import structlog
from sqlmodel import create_engine, Session
from sqlalchemy import Engine
from opsmate.dbq.dbq import enqueue_task, Worker, SQLModel
from typing import Dict, Any, List
import asyncio
import uuid
import json
from opsmate.dino import dino
from datetime import datetime

logger = structlog.get_logger()

engine: Engine | None = None


def init_engine(e: Engine | None = None):
    global engine
    engine = e or create_engine(
        config.db_url, connect_args={"check_same_thread": False}
    )


@dino(
    model="gpt-4o-mini",
    response_model=List[Category],
)
async def categorize(text: str) -> str:
    f"""
    You are a world class expert in categorizing text.
    Please categorise the text into one or more unique categories:
    """
    return text


async def categorize_kb(kb: Dict[str, Any]):
    categories = await categorize(kb["content"])
    kb["categories"] = [cat.value for cat in categories]
    return kb


async def chunk_and_store(
    ingestor_type: str = "",
    ingestor_config: Dict[str, Any] = {},
    doc: Dict[str, Any] = {},
):
    doc = Document(**doc)
    ingestion = ingestor_from_config(ingestor_type, ingestor_config)
    db_conn = await aconn()
    table = await db_conn.open_table("knowledge_store")

    data_provider = ingestion.data_source_provider()
    data_source = ingestion.data_source()
    path = doc.metadata["path"]

    kbs = []
    async for chunk in ingestion.chunking_document(doc):
        kbs.append(
            {
                "uuid": str(uuid.uuid4()),
                "id": chunk.id,
                # "summary": chunk.metadata["summary"],
                "categories": [],
                "data_source_provider": data_provider,
                "data_source": data_source,
                "metadata": json.dumps(chunk.metadata),
                "path": path,
                "content": chunk.content,
                "created_at": datetime.now(),
            }
        )

    tasks = [categorize_kb(kb) for kb in kbs]
    await asyncio.gather(*tasks)

    logger.info(
        "deleting chunks from data source",
        data_source_provider=data_provider,
        data_source=data_source,
        path=path,
    )
    await table.delete(
        f"data_source_provider = '{data_provider}'"
        f"AND data_source = '{data_source}'"
        f"AND path = '{path}'"
    )

    await table.add(kbs)

    logger.info(
        "chunks stored",
        data_provider=data_provider,
        data_source=data_source,
        path=path,
        ingestor_type=ingestor_type,
        ingestor_config=ingestor_config,
        num_kbs=len(kbs),
    )


async def ingest(ingestor_type: str, ingestor_config: Dict[str, Any]):
    with Session(engine) as session:
        ingestion = ingestor_from_config(ingestor_type, ingestor_config)

        async for doc in ingestion.load():
            logger.info(
                "ingesting document",
                ingestor_type=ingestor_type,
                ingestor_config=ingestor_config,
                doc_path=doc.metadata["path"],
            )
            enqueue_task(
                session,
                chunk_and_store,
                ingestor_type=ingestor_type,
                ingestor_config=ingestor_config,
                doc=doc.model_dump(),
            )


def ingestor_from_config(name: str, config: Dict[str, Any]):
    if name == "github":
        return GithubIngestion(**config)
    elif name == "fs":
        return FsIngestion(**config)
    else:
        raise ValueError(f"Unknown ingestor type: {name}")
