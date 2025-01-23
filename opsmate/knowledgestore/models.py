import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from lancedb.index import FTS
from pydantic import Field
from opsmate.libs.config import config
from typing import List
import uuid
from lancedb.rerankers import OpenaiReranker
from enum import Enum

registry = get_registry()

# embeddings is the embedding function used to embed the knowledge store
embeddings = registry.get(config.embedding_registry_name).create(
    name=config.embedding_model_name
)


class Category(Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTENANCE = "maintenance"
    APPLICATION = "application"
    INFRASTRUCTURE = "infrastructure"
    PRODUCTION = "production"


class KnowledgeStore(LanceModel):
    uuid: str = Field(description="The uuid of the runbook", default_factory=uuid.uuid4)
    # summary: str = Field(description="The summary of the knowledge")
    categories: List[str] = Field(description="The categories of the knowledge")
    data_source_provider: str = Field(description="The provider of the data source")
    data_source: str = Field(description="The source of the knowledge")
    metadata: str = Field(description="The metadata of the knowledge json encoded")
    path: str = Field(description="The path of the knowledge", default="")
    vector: Vector(embeddings.ndims()) = embeddings.VectorField()
    content: str = (
        embeddings.SourceField()
    )  # source field indicates the field will be embed


openai_reranker = OpenaiReranker(model_name="gpt-4o-mini", column="content")


async def aconn():
    """
    Create an async connection to the lancedb based on the config.embeddings_db_path
    """
    return await lancedb.connect_async(config.embeddings_db_path)


def conn():
    """
    Create a connection to the lancedb based on the config.embeddings_db_path
    """
    return lancedb.connect(config.embeddings_db_path)


async def init_table():
    """
    init the knowledge store table based on the config.embeddings_db_path
    """
    db = await aconn()
    table = await db.create_table(
        "knowledge_store", schema=KnowledgeStore, exist_ok=True
    )
    await table.create_index("content", config=FTS())
    return table
