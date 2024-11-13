from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

default_db_path = str(Path.home() / "data" / "opsmate-embeddings")


class Config(BaseSettings):
    embeddings_db_path: str = Field(
        default=default_db_path, description="The path to the lance db"
    )
    embedding_registry_name: str = Field(
        default="openai", description="The name of the embedding registry"
    )
    embedding_model_name: str = Field(
        default="text-embedding-ada-002", description="The name of the embedding model"
    )


config = Config()
