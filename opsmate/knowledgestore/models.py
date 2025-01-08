import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from pydantic import Field, BaseModel
from opsmate.libs.config import config
from typing import Dict, List
import structlog
import uuid

registry = get_registry()
func = registry.get(config.embedding_registry_name).create(
    name=config.embedding_model_name
)


class KnowledgeStore(LanceModel):
    uuid: str = Field(description="The uuid of the runbook", default_factory=uuid.uuid4)
    summary: str = Field(description="The summary of the knowledge")
    categories: List[str] = Field(description="The categories of the knowledge")
    data_source_provider: str = Field(description="The provider of the data source")
    data_source: str = Field(description="The source of the knowledge")
    path: str = Field(description="The path of the knowledge", default="")
    vector: Vector(func.ndims()) = func.VectorField()
    content: str = func.SourceField()  # source field indicates the field will be embed


async def init_db():
    return await lancedb.connect_async(config.embeddings_db_path)


async def init_table():
    db = await init_db()
    table = await db.create_table(
        "knowledge_store", schema=KnowledgeStore, exist_ok=True
    )
