from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, List, Callable, Awaitable
from pydantic import BaseModel, Field, model_validator
from opsmate.textsplitters import TextSplitter, RecursiveTextSplitter
from opsmate.textsplitters.base import Chunk


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

    async def ingest(self):
        async for document in self.load():
            print(document)
            for chunk in self.splitter.split_text(document.content):
                print(chunk)
                ch = chunk.model_copy()
                for key, value in document.metadata.items():
                    ch.metadata[key] = value
                if self.post_chunk_hooks:
                    for hook in self.post_chunk_hooks:
                        ch = await hook(ch)
                yield ch

    @abstractmethod
    async def load(self) -> AsyncGenerator[Document, None]:
        pass
