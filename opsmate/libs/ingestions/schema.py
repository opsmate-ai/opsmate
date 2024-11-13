import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from pydantic import Field


db = lancedb.connect("./data/opsmate-embeddings")
func = get_registry().get("openai").create(name="text-embedding-ada-002")


class Runbook(LanceModel):
    filename: str = Field(description="The name of the file")
    heading: str = Field(description="The heading of the file")
    content: str = func.SourceField()
    vector: Vector(func.ndims()) = func.VectorField()


runbooks_table = db.create_table("runbooks", schema=Runbook, mode="overwrite")
