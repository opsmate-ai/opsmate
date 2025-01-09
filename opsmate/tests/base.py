import tempfile
import os
import pytest
from opsmate.libs.config import Config
import structlog

logger = structlog.get_logger()


class BaseTestCase:
    @pytest.fixture(scope="session", autouse=True)
    def setup_embeddings_db(self):
        pid = os.getpid()
        prefix = f"opsmate-embeddings-{pid}"
        tempdir = tempfile.mkdtemp(prefix=prefix)
        config = Config(
            embeddings_db_path=tempdir,
        )
        logger.info("Created temp dir for embeddings", path=config.embeddings_db_path)
        # DatabaseConnection.get_instance()

        yield

        logger.info("Removing temp dir for embeddings", path=config.embeddings_db_path)
        os.system(f"rm -rf {config.embeddings_db_path}")
