from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Dict

default_db_path = str(Path.home() / "data" / "opsmate-embeddings")


fs_embedding_desc = """
The configuration for the fs embeddings.

This is a dictionary with the following pattern of path=glob_pattern

Example:

your_repo_path=*.md
your_repo_path2=*.txt
"""

github_embedding_desc = """
The configuration for the github embeddings

This is a dictionary with the following pattern of owner/repo:branch=glob_pattern

If the branch is not specified, it will default to main.

Example:

opsmate/opsmate=main=*.md
opsmate/opsmate2=main=*.txt
"""


class Config(BaseSettings):
    db_url: str = Field(default="sqlite:///:memory:", alias="OPSMATE_DB_URL")

    embeddings_db_path: str = Field(
        default=default_db_path, description="The path to the lance db"
    )
    embedding_registry_name: str = Field(
        default="openai", description="The name of the embedding registry"
    )
    embedding_model_name: str = Field(
        default="text-embedding-ada-002", description="The name of the embedding model"
    )
    fs_embeddings_config: Dict[str, str] = Field(
        default={}, description=fs_embedding_desc
    )
    github_embeddings_config: Dict[str, str] = Field(
        default={}, description=github_embedding_desc
    )
    categorise: bool = Field(
        default=True, description="Whether to categorise the embeddings"
    )


config = Config()
