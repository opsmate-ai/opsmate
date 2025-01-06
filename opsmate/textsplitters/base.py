from abc import ABC, abstractmethod
from typing import List


class TextSplitter(ABC):
    default_separators = ["\n\n", "\n", " ", ""]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = [],
    ):
        """
        Initialize the text splitter
        Args:
            chunk_size: The size of the chunks to split the text into
            chunk_overlap: The overlap between the chunks
            separator: The separators to use to split the text
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        if separators:
            self.separators = separators
        else:
            self.separators = self.default_separators

    @abstractmethod
    def split_text(self, text: str) -> List[str]: ...
