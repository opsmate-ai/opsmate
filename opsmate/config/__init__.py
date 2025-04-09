from pydantic_settings import (
    BaseSettings,
    YamlConfigSettingsSource,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
)
from pydantic import Field, model_validator, field_validator
from pathlib import Path
from typing import Dict, Any, Self, Tuple, Type
import structlog
import logging
from sqlmodel import create_engine, text
import importlib.util
import json
import os

logger = structlog.get_logger(__name__)

default_embeddings_db_path = str(Path.home() / ".opsmate" / "embeddings")
default_db_url = f"sqlite:///{str(Path.home() / '.opsmate' / 'opsmate.db')}"
default_config_file = str(Path.home() / ".opsmate" / "config.yaml")
default_plugins_dir = str(Path.home() / ".opsmate" / "plugins")
default_contexts_dir = str(Path.home() / ".opsmate" / "contexts")
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

DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"
DEFAULT_SENTENCE_TRANSFORMERS_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file=default_config_file, env_file=".env", populate_by_name=True
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            YamlConfigSettingsSource(settings_cls),
        )

    db_url: str = Field(default=default_db_url, alias="OPSMATE_DB_URL")

    plugins_dir: str = Field(
        default=default_plugins_dir,
        alias="OPSMATE_PLUGINS_DIR",
    )
    contexts_dir: str = Field(
        default=default_contexts_dir,
        alias="OPSMATE_CONTEXTS_DIR",
    )

    embeddings_db_path: str = Field(
        default=default_embeddings_db_path,
        description="The path to the lance db. When s3:// is used for AWS S3, az:// is used for Azure Blob Storage, and gs:// is used for Google Cloud Storage",
        alias="OPSMATE_EMBEDDINGS_DB_PATH",
    )
    embedding_registry_name: str = Field(
        default="",
        choices=["openai", "sentence-transformers"],
        description="The name of the embedding registry",
        alias="OPSMATE_EMBEDDING_REGISTRY_NAME",
    )
    embedding_model_name: str = Field(
        default="",
        description="The name of the embedding model",
        alias="OPSMATE_EMBEDDING_MODEL_NAME",
    )
    reranker_name: str = Field(
        default="",
        description="The name of the reranker model",
        choices=["answerdotai", "openai", "cohere", "rrf", ""],
        alias="OPSMATE_RERANKER_NAME",
    )
    fs_embeddings_config: Dict[str, str] = Field(
        default={}, description=fs_embedding_desc, alias="OPSMATE_FS_EMBEDDINGS_CONFIG"
    )
    github_embeddings_config: Dict[str, str] = Field(
        default={},
        description=github_embedding_desc,
        alias="OPSMATE_GITHUB_EMBEDDINGS_CONFIG",
    )
    categorise: bool = Field(
        default=True,
        description="Whether to categorise the embeddings",
        alias="OPSMATE_CATEGORISE",
    )
    splitter_config: Dict[str, Any] = Field(
        default={
            "splitter": "markdown_header",
            "headers_to_split_on": (
                ("##", "h2"),
                ("###", "h3"),
            ),
        },
        description="The splitter to use for the ingestion",
        alias="OPSMATE_SPLITTER_CONFIG",
    )

    loglevel: str = Field(default="INFO", alias="OPSMATE_LOGLEVEL")

    @field_validator("embedding_registry_name")
    def validate_embedding_registry_name(cls, v):
        if v == "":
            if cls.transformers_available():
                return "sentence-transformers"
            else:
                return "openai"
        return v

    @field_validator("embedding_model_name")
    def validate_embedding_model_name(cls, v):
        if v == "":
            if cls.transformers_available():
                return DEFAULT_SENTENCE_TRANSFORMERS_EMBEDDING_MODEL
            else:
                return DEFAULT_OPENAI_EMBEDDING_MODEL
        return v

    @classmethod
    def transformers_available(cls):
        return importlib.util.find_spec("transformers") is not None

    def set_loglevel(self) -> Self:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.getLevelNamesMapping()[self.loglevel]
            ),
        )
        return self

    @model_validator(mode="after")
    def mkdir(self):
        opsmate_dir = str(Path.home() / ".opsmate")
        Path(opsmate_dir).mkdir(parents=True, exist_ok=True)
        Path(self.plugins_dir).mkdir(parents=True, exist_ok=True)
        if not (
            self.embeddings_db_path.startswith("s3://")
            or self.embeddings_db_path.startswith("az://")
            or self.embeddings_db_path.startswith("gs://")
        ):
            Path(self.embeddings_db_path).mkdir(parents=True, exist_ok=True)
        Path(self.contexts_dir).mkdir(parents=True, exist_ok=True)
        return self

    def db_engine(self):
        logger.info("Creating db engine", db_url=self.db_url)
        engine = create_engine(
            self.db_url,
            connect_args={"check_same_thread": False, "timeout": 20},
            # echo=True,
        )
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.close()

        if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            SQLAlchemyInstrumentor().instrument(
                engine=engine,
                enable_commenter=True,
                commenter_options={"comment_style": "sqlalchemy"},
            )

        return engine

    def serialize_to_env(self):
        """Serialize the config to a dictionary of environment variables"""

        env_vars = {}

        for field_name, field_value in self.model_dump().items():
            if field_value is None:
                continue

            field_info = self.model_fields.get(field_name)
            alias = field_info.alias

            if isinstance(field_value, dict):
                env_vars[alias] = json.dumps(field_value)
            elif isinstance(field_value, list) or isinstance(field_value, tuple):
                env_vars[alias] = json.dumps(field_value)
            else:
                env_vars[alias] = str(field_value)

        for key, value in env_vars.items():
            os.environ[key] = value


config = Config()
