import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from lancedb.index import FTS
from pydantic import Field, BaseModel
from opsmate.libs.config import config
from typing import Dict, List
import structlog
import uuid
from lancedb.rerankers import OpenaiReranker

registry = get_registry()
embeddings = registry.get(config.embedding_registry_name).create(
    name=config.embedding_model_name
)


class KnowledgeStore(LanceModel):
    uuid: str = Field(description="The uuid of the runbook", default_factory=uuid.uuid4)
    # summary: str = Field(description="The summary of the knowledge")
    categories: List[str] = Field(description="The categories of the knowledge")
    data_source_provider: str = Field(description="The provider of the data source")
    data_source: str = Field(description="The source of the knowledge")
    path: str = Field(description="The path of the knowledge", default="")
    vector: Vector(embeddings.ndims()) = embeddings.VectorField()
    content: str = (
        embeddings.SourceField()
    )  # source field indicates the field will be embed


openai_reranker = OpenaiReranker(model_name="gpt-4o-mini", column="content")


async def aconn():
    return await lancedb.connect_async(config.embeddings_db_path)


def conn():
    return lancedb.connect(config.embeddings_db_path)


async def init_table():
    db = await aconn()
    table = await db.create_table(
        "knowledge_store", schema=KnowledgeStore, exist_ok=True
    )
    await table.create_index("content", config=FTS())
    return table
