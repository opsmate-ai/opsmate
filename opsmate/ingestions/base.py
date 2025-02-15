from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, List, Callable, Awaitable
from pydantic import BaseModel, Field, model_validator
from opsmate.textsplitters import TextSplitter, RecursiveTextSplitter
from opsmate.textsplitters.base import Chunk
import structlog

logger = structlog.get_logger(__name__)


class Document(BaseModel):
    metadata: dict = Field(default_factory=dict)
    content: str


PostChunkHook = Callable[[Chunk], Awaitable[Chunk]]


class BaseIngestion(ABC, BaseModel):
    class Config:
        arbitrary_types_allowed = True

    splitter: Optional[TextSplitter] = Field(default=None)
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=0)
    separators: Optional[List[str]] = None
    post_chunk_hooks: Optional[List[PostChunkHook]] = None

    @model_validator(mode="after")
    @classmethod
    def load_splitter(cls, v):
        if v.splitter is None:
            v.splitter = RecursiveTextSplitter(
                chunk_size=v.chunk_size,
                chunk_overlap=v.chunk_overlap,
                separators=v.separators,
            )
        return v

    async def chunking(self):
        """
        Chunk the documents coming from the ingestion source.
        """
        async for document in self.load():
            async for chunk in self.chunking_document(document):
                yield chunk

    async def chunking_document(self, document: Document):
        """
        Chunk the individual document.
        """
        for chunk_idx, chunk in enumerate(self.splitter.split_text(document.content)):
            logger.info("chunking document", document=document.metadata["path"])
            ch = chunk.model_copy()
            for key, value in document.metadata.items():
                ch.metadata[key] = value
            ch.id = chunk_idx
            ch.metadata["data_source"] = self.data_source()
            ch.metadata["data_source_provider"] = self.data_source_provider()
            if self.post_chunk_hooks:
                for hook in self.post_chunk_hooks:
                    ch = await hook(ch)
            yield ch

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
