from .base import BaseIngestion
from .fs import FsIngestion
from .github import GithubIngestion
from typing import List
from opsmate.config import Config
import structlog
from opsmate.ingestions.jobs import ingest
from sqlmodel import Session
from opsmate.dbq.dbq import enqueue_task
from sqlalchemy import Engine
from opsmate.knowledgestore.models import init_table

logger = structlog.get_logger(__name__)

__all__ = ["BaseIngestion", "FsIngestion", "GithubIngestion"]


def ingestions_from_config(cfg: Config) -> List[BaseIngestion]:
    ingestions = []
    github_ingestions = GithubIngestion.from_configmap(cfg.github_embeddings_config)
    fs_ingestions = FsIngestion.from_configmap(cfg.fs_embeddings_config)
    ingestions.extend(github_ingestions)
    ingestions.extend(fs_ingestions)

    return ingestions


async def ingest_from_config(
    cfg: Config, engine: Engine | None = None
) -> List[BaseIngestion]:
    """
    Ingest the data based on the env var config.
    """
    ingestions = ingestions_from_config(cfg)

    await init_table()
    # db_conn = await aconn()
    # table = await db_conn.open_table("knowledge_store")

    with Session(engine) as session:
        for ingestion in ingestions:
            if ingestion.data_source_provider() == "github":
                enqueue_task(
                    session,
                    ingest,
                    ingestor_type="github",
                    ingestor_config={
                        "repo": ingestion.repo,
                        "branch": ingestion.branch,
                        "path": ingestion.path,
                        "glob": ingestion.glob,
                    },
                    splitter_config=cfg.splitter_config,
                )
            elif ingestion.data_source_provider() == "fs":
                enqueue_task(
                    session,
                    ingest,
                    ingestor_type="fs",
                    ingestor_config={
                        "local_path": ingestion.local_path,
                        "glob_pattern": ingestion.glob_pattern,
                    },
                    splitter_config=cfg.splitter_config,
                )

        logger.info("Ingestion tasks enqueued")
