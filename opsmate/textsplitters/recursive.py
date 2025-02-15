from typing import List
from .base import TextSplitter, Chunk


class RecursiveTextSplitter(TextSplitter):
    def split_text(self, text: str) -> List[str]:
        """
        Split the text into chunks of size chunk_size with overlap chunk_overlap
        """
        splits = self._split_text(text, 0)
        splits = self._merge_splits(splits)
        return self._handle_overlap(splits)

    def _split_text(self, text: str, separatorLevel: int) -> List[Chunk]:
        if separatorLevel == len(self.separators):
            return [
                Chunk(
                    content=text,
                    metadata={"seperator": self.separators[-1]},
                )
            ]

        if len(text) <= self.chunk_size:
            return [
                Chunk(
                    content=text,
                    metadata={"seperator": self.separators[separatorLevel - 1]},
                )
            ]

        separator = self.separators[separatorLevel]
        splits = text.split(separator)
        splits = [split for split in splits if split]

        result = []
        for split in splits:
            result.extend(self._split_text(split, separatorLevel + 1))

        return result

    def _merge_splits(self, splits: List[Chunk]) -> List[Chunk]:
        result = []
        idx = 0
        while idx < len(splits):
            sep1, add = splits[idx].metadata["seperator"], splits[idx].content
            idx += 1
            while idx < len(splits):
                sep2, chunk = splits[idx].metadata["seperator"], splits[idx].content
                if len(add) + len(sep2) + len(chunk) <= self.chunk_size:
                    add += sep2 + chunk
                    idx += 1
                else:
                    break
            result.append(
                Chunk(
                    content=add,
                    metadata={"seperator": sep1},
                )
            )
        return result

    def _handle_overlap(self, splits: List[Chunk]) -> List[Chunk]:
        result = []
        for idx, split in enumerate(splits):
            sep1, add = split.metadata["seperator"], split.content
            overlap_remain = self.chunk_overlap + self.chunk_size - len(add)

            while overlap_remain > 0:
                for idx2 in range(idx + 1, len(splits)):
                    sep2, chunk = (
                        splits[idx2].metadata["seperator"],
                        splits[idx2].content,
                    )
                    if len(sep2) + len(chunk) <= overlap_remain:
                        add += sep2 + chunk
                        overlap_remain -= len(chunk) - len(sep2)
                    else:
                        break
                break
            result.append(
                Chunk(
                    content=add,
                    metadata={"seperator": sep1},
                )
            )

        return result
