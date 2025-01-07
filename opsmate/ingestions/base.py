from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, List, Callable, Awaitable
from pydantic import BaseModel, Field
from opsmate.textsplitters import TextSplitter, RecursiveTextSplitter
from opsmate.textsplitters.base import Chunk


class Document(BaseModel):
    metadata: dict = Field(default_factory=dict)
    content: str


PostChunkHook = Callable[[Chunk], Awaitable[Chunk]]


class BaseIngestion(ABC):
    def __init__(
        self,
        splitter: Optional[TextSplitter] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 0,
        separators: Optional[List[str]] = None,
        post_chunk_hooks: Optional[List[PostChunkHook]] = None,
    ):
        self.splitter = splitter
        if self.splitter is None:
            self.splitter = RecursiveTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=separators,
            )
        self.post_chunk_hooks = post_chunk_hooks

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
