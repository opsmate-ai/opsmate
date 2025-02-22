from sqlmodel import (
    SQLModel as _SQLModel,
    Field,
    Session,
    select,
    Relationship,
    JSON,
    Column,
)
from sqlalchemy.orm import registry
from datetime import datetime, UTC
from sqlalchemy import MetaData
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class SQLModel(_SQLModel, registry=registry()):
    metadata = MetaData()


class IngestionRecord(SQLModel, table=True):
    __tablename__ = "ingestions"
    id: int = Field(primary_key=True, sa_column_kwargs={"autoincrement": True})
    data_source_provider: str = Field(default="github", nullable=False)
    data_source: str = Field(nullable=False)
    branch: str = Field(
        default="main",
        nullable=False,
        description="Branch to ingest from, used by GithubIngestion",
    )
    glob: str = Field(default="**/*.md", nullable=False)
    created_at: datetime = Field(default=datetime.now(UTC))
    updated_at: datetime = Field(default=datetime.now(UTC))

    documents: List["DocumentRecord"] = Relationship(
        back_populates="ingestion",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    @classmethod
    async def find_or_create(
        cls, session: Session, ingestion_type: str, ingestion_config: Dict[str, Any]
    ):
        glob = ingestion_config.get("glob") or ingestion_config.get("glob_pattern")
        data_source = ingestion_config.get("repo") or ingestion_config.get("local_path")
        branch = ingestion_config.get("branch") or "main"
        ingestion = session.exec(
            select(cls).where(
                cls.data_source_provider == ingestion_type,
                cls.data_source == data_source,
                cls.glob == glob,
                cls.branch == branch,
            )
        ).first()

        if ingestion is None:
            ingestion = cls(
                data_source_provider=ingestion_type,
                data_source=data_source,
                glob=glob,
                branch=branch,
            )
            session.add(ingestion)
            session.commit()
            session.refresh(ingestion)
        logger.info(
            "ingestion record found or created",
            ingestion_id=ingestion.id,
            ingestion_type=ingestion_type,
            ingestion_config=ingestion_config,
        )
        return ingestion

    @classmethod
    async def find_by_id(cls, session: Session, id: int):
        return session.exec(select(cls).where(cls.id == id)).first()

    async def ingest_config(self):
        match self.data_source_provider:
            case "github":
                return {
                    "repo": self.data_source,
                    "glob": self.glob,
                    "branch": self.branch,
                }
            case "fs":
                return {
                    "local_path": self.data_source,
                    "glob_pattern": self.glob,
                }
            case _:
                raise ValueError(
                    f"Unsupported data source provider: {self.data_source_provider}"
                )


class DocumentRecord(SQLModel, table=True):
    __tablename__ = "documents"
    id: int = Field(primary_key=True, sa_column_kwargs={"autoincrement": True})

    ingestion_id: int = Field(foreign_key="ingestions.id")
    ingestion: IngestionRecord = Relationship(back_populates="documents")

    path: str = Field(nullable=False)
    chunk_count: int = Field(default=0)
    sha: str = Field(nullable=False)
    chunk_config: Dict[str, Any] = Field(sa_column=Column(JSON))

    created_at: datetime = Field(default=datetime.now(UTC))
    updated_at: datetime = Field(default=datetime.now(UTC))

    @classmethod
    async def find_by_ingestion_id_and_path(
        cls, session: Session, ingestion_id: int, path: str
    ):
        return session.exec(
            select(cls).where(cls.ingestion_id == ingestion_id, cls.path == path)
        ).first()

    @classmethod
    async def find_or_create(
        cls,
        session: Session,
        ingestion_id: int,
        path: str,
        sha: str,
        chunk_config: Dict[str, Any],
    ):
        document = session.exec(
            select(cls).where(cls.ingestion_id == ingestion_id, cls.path == path)
        ).first()
        if document is None:
            document = cls(
                ingestion_id=ingestion_id,
                path=path,
                sha=sha,
                chunk_config=chunk_config,
            )
        else:
            document.sha = sha
            document.chunk_config = chunk_config

        session.add(document)
        session.commit()
        session.refresh(document)
        return document

    def update_chunk_count(self, session: Session, chunk_count: int):
        self.chunk_count = chunk_count
        self.updated_at = datetime.now(UTC)
        session.add(self)
        session.commit()
