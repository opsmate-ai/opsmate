from opsmate.knowledgestore.models import aconn, Category
from opsmate.ingestions.base import Document
from opsmate.ingestions.chunk import chunk_document
from opsmate.ingestions.fs import FsIngestion
from opsmate.ingestions.github import GithubIngestion
from opsmate.libs.config import config
import structlog
from opsmate.dbq.dbq import enqueue_task
from opsmate.dino import dino
from typing import Dict, Any, List
from datetime import datetime
from opsmate.textsplitters import splitter_from_config
import asyncio
import uuid
import json

logger = structlog.get_logger()


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
    splitter_config: Dict[str, Any] = {},
    doc: Dict[str, Any] = {},
    ctx: Dict[str, Any] = {},
):
    doc = Document(**doc)
    splitter = splitter_from_config(splitter_config)
    db_conn = await aconn()
    table = await db_conn.open_table("knowledge_store")

    path = doc.metadata["path"]

    kbs = []
    async for chunk in chunk_document(splitter=splitter, document=doc):
        kbs.append(
            {
                "uuid": str(uuid.uuid4()),
                "id": chunk.id,
                # "summary": chunk.metadata["summary"],
                "categories": [],
                "data_source_provider": doc.data_provider,
                "data_source": doc.data_source,
                "metadata": json.dumps(chunk.metadata),
                "path": path,
                "content": chunk.content,
                "created_at": datetime.now(),
            }
        )

    if config.categorise:
        tasks = [categorize_kb(kb) for kb in kbs]
        await asyncio.gather(*tasks)

    logger.info(
        "deleting chunks from data source",
        data_source_provider=doc.data_provider,
        data_source=doc.data_source,
        path=path,
    )
    await table.delete(
        f"data_source_provider = '{doc.data_provider}'"
        f"AND data_source = '{doc.data_source}'"
        f"AND path = '{path}'"
    )

    await table.add(kbs)

    logger.info(
        "chunks stored",
        data_provider=doc.data_provider,
        data_source=doc.data_source,
        path=path,
        num_kbs=len(kbs),
    )


async def ingest(
    ingestor_type: str,
    ingestor_config: Dict[str, Any],
    splitter_config: Dict[str, Any] = {},
    ctx: Dict[str, Any] = {},
):
    session = ctx["session"]

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
            splitter_config=splitter_config,
            doc=doc.model_dump(),
        )


def ingestor_from_config(name: str, config: Dict[str, Any]):
    if name == "github":
        return GithubIngestion(**config)
    elif name == "fs":
        return FsIngestion(**config)
    else:
        raise ValueError(f"Unknown ingestor type: {name}")
