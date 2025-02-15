from .base import TextSplitter
from .recursive import RecursiveTextSplitter
from .markdown_header import MarkdownHeaderTextSplitter
from typing import Dict, Any

__all__ = ["TextSplitter", "RecursiveTextSplitter", "MarkdownHeaderTextSplitter"]

RECURSIVE_SPLITTER = "recursive"
MARKDOWN_HEADER_SPLITTER = "markdown_header"

SPLITTERS = {
    RECURSIVE_SPLITTER: RecursiveTextSplitter,
    MARKDOWN_HEADER_SPLITTER: MarkdownHeaderTextSplitter,
}


def splitter_from_config(config: Dict[str, Any]) -> TextSplitter:
    name = config.pop("splitter", RECURSIVE_SPLITTER)
    if name not in SPLITTERS:
        raise ValueError(
            f"Unknown splitter type: {name}, must be one of {', '.join(SPLITTERS.keys())}"
        )
    return SPLITTERS[name](**config)
