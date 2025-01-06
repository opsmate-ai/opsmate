from typing import List, Tuple
from .base import TextSplitter


class RecursiveTextSplitter(TextSplitter):
    def split_text(self, text: str) -> List[str]:
        """
        Split the text into chunks of size chunk_size with overlap chunk_overlap
        """
        splits = self._split_text(text, 0)
        splits = self._merge_splits(splits)
        return self._handle_overlap(splits)

    def _split_text(self, text: str, separatorLevel: int) -> List[Tuple[str, str]]:
        if separatorLevel == len(self.separators):
            return [(self.separators[-1], text)]

        if len(text) <= self.chunk_size:
            return [(self.separators[separatorLevel - 1], text)]

        separator = self.separators[separatorLevel]
        splits = text.split(separator)
        splits = [split for split in splits if split]

        result = []
        for split in splits:
            result.extend(self._split_text(split, separatorLevel + 1))

        return result

    def _merge_splits(self, splits: List[Tuple[str, str]]) -> List[str]:
        result = []
        idx = 0
        while idx < len(splits):
            sep1, add = splits[idx]
            idx += 1
            while idx < len(splits):
                sep2, chunk = splits[idx]
                if len(add) + len(sep2) + len(chunk) <= self.chunk_size:
                    add += sep2 + chunk
                    idx += 1
                else:
                    break
            result.append((sep1, add))
        return result

    def _handle_overlap(self, splits: List[Tuple[str, str]]) -> str:
        result = []
        for idx, split in enumerate(splits):
            _, add = split
            overlap_remain = self.chunk_overlap + self.chunk_size - len(add)

            while overlap_remain > 0:
                for idx2 in range(idx + 1, len(splits)):
                    sep, chunk = splits[idx2]
                    if len(sep) + len(chunk) <= overlap_remain:
                        add += sep + chunk
                        overlap_remain -= len(chunk) - len(sep)
                    else:
                        break
                break
            result.append(add)

        return result
