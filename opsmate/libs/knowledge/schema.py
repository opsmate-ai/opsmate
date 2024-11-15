import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from pydantic import Field
from opsmate.libs.config import config
import threading
import structlog
import uuid

logger = structlog.get_logger()


class DatabaseConnection:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        if DatabaseConnection._instance is not None:
            raise RuntimeError("use get_instance() to get the instance")
        self.db = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls.__new__(cls)
                    cls._instance.db = lancedb.connect(config.embeddings_db_path)
                    cls.init_db(cls._instance.db)

                    return cls._instance.db
        return cls._instance.db

    @classmethod
    def init_db(cls, db: lancedb.DBConnection):
        logger.info("creating runbooks table")
        db.create_table("runbooks", schema=Runbook, exist_ok=True)


func = (
    get_registry()
    .get(config.embedding_registry_name)
    .create(name=config.embedding_model_name)
)


class Runbook(LanceModel):
    uuid: str = Field(description="The uuid of the runbook", default_factory=uuid.uuid4)
    filename: str = Field(description="The name of the file")
    heading: str = Field(description="The heading of the file")
    content: str = func.SourceField()
    vector: Vector(func.ndims()) = func.VectorField()


def get_runbooks_table():
    """
    Get the runbooks table
    """

    db = DatabaseConnection.get_instance()
    return db.open_table("runbooks")
