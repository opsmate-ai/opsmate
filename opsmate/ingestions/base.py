from abc import ABC, abstractmethod
from typing import AsyncGenerator, Callable, Awaitable
from pydantic import BaseModel, Field
from opsmate.textsplitters.base import Chunk
import structlog

logger = structlog.get_logger(__name__)


class Document(BaseModel):
    metadata: dict = Field(default_factory=dict)
    data_provider: str = Field(default="unknown")
    data_source: str = Field(default="unknown")
    content: str


PostChunkHook = Callable[[Chunk], Awaitable[Chunk]]


class BaseIngestion(ABC, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def load(self) -> AsyncGenerator[Document, None]:
        """
        Load the documents from the ingestion source.
        """
        pass

    @abstractmethod
    def data_source(self) -> str:
        """
        The data source of the ingestion.
        """
        pass

    @abstractmethod
    def data_source_provider(self) -> str:
        """
        The data source provider of the ingestion.
        """
        pass
