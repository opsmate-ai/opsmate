import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from pydantic import Field
from opsmate.libs.config import config

db = lancedb.connect(config.embeddings_db_path)
func = (
    get_registry()
    .get(config.embedding_registry_name)
    .create(name=config.embedding_model_name)
)


class Runbook(LanceModel):
    filename: str = Field(description="The name of the file")
    heading: str = Field(description="The heading of the file")
    content: str = func.SourceField()
    vector: Vector(func.ndims()) = func.VectorField()


runbooks_table = db.create_table("runbooks", schema=Runbook, mode="overwrite")
