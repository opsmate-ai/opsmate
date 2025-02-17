from opsmate.ingestions.base import Document
from opsmate.textsplitters import TextSplitter
import structlog

logger = structlog.get_logger(__name__)


async def chunk_document(splitter: TextSplitter, document: Document):
    """
    Chunk the individual document.
    """
    for chunk_idx, chunk in enumerate(splitter.split_text(document.content)):
        logger.info(
            "chunking document", document=document.metadata["path"], chunk_idx=chunk_idx
        )
        ch = chunk.model_copy()
        for key, value in document.metadata.items():
            ch.metadata[key] = value
        ch.id = chunk_idx
        ch.metadata["data_source"] = document.data_source
        ch.metadata["data_source_provider"] = document.data_provider

        yield ch
