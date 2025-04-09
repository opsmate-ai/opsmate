import pytest
from opsmate.ingestions import ingestions_from_config
from opsmate.tests.base import BaseTestCase
from opsmate.config import Config
from opsmate.ingestions import GithubIngestion, FsIngestion
import os


class TestIngestions(BaseTestCase):
    def test_ingestions_from_env(self):
        old_token = os.getenv("GITHUB_TOKEN")
        os.environ["GITHUB_TOKEN"] = "env-token"
        cfg = Config()
        cfg.github_embeddings_config = {
            "opsmate/opsmate:dev": "*.md",
            "opsmate/opsmate2": "*.txt",
        }
        cfg.fs_embeddings_config = {
            "your_repo_path": "*.md",
            "your_repo_path2": "*.txt",
        }
        ingestions = ingestions_from_config(cfg)
        assert len(ingestions) == 4
        assert isinstance(ingestions[0], GithubIngestion)
        assert ingestions[0].data_source_provider() == "github"
        assert ingestions[0].data_source() == "opsmate/opsmate"
        assert ingestions[0].repo == "opsmate/opsmate"
        assert ingestions[0].branch == "dev"
        assert ingestions[0].glob == "*.md"

        assert isinstance(ingestions[1], GithubIngestion)
        assert ingestions[1].data_source_provider() == "github"
        assert ingestions[1].data_source() == "opsmate/opsmate2"
        assert ingestions[1].repo == "opsmate/opsmate2"
        assert ingestions[1].branch == "main"
        assert ingestions[1].glob == "*.txt"

        assert isinstance(ingestions[2], FsIngestion)
        assert ingestions[2].data_source_provider() == "fs"
        assert ingestions[2].data_source() == "your_repo_path/*.md"
        assert ingestions[2].local_path == "your_repo_path"
        assert ingestions[2].glob_pattern == "*.md"

        assert isinstance(ingestions[3], FsIngestion)
        assert ingestions[3].data_source_provider() == "fs"
        assert ingestions[3].data_source() == "your_repo_path2/*.txt"
        assert ingestions[3].local_path == "your_repo_path2"
        assert ingestions[3].glob_pattern == "*.txt"

        if old_token:
            os.environ["GITHUB_TOKEN"] = old_token
        else:
            del os.environ["GITHUB_TOKEN"]
