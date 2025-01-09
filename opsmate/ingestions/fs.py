from typing import AsyncGenerator
from .base import BaseIngestion, Document
from pydantic import BaseModel, Field
from glob import glob
from os import path
from pathlib import Path
from typing import Dict, List


class FsIngestion(BaseIngestion):
    local_path: str = Field(..., description="The local path to the files")
    glob_pattern: str = Field("**/*", description="The glob pattern to match the files")

    async def load(self) -> AsyncGenerator[Document, None]:
        glob_pattern = path.join(self.local_path, self.glob_pattern)
        files = glob(glob_pattern, recursive=True)
        for filename in files:
            # skip if filename is a directory
            if path.isdir(filename):
                continue
            with open(filename, "r") as f:
                content = f.read()
            base_name = path.basename(filename)
            path_name = path.join(
                path.dirname(filename.replace(self.local_path, "")),
                base_name,
            )

            yield Document(
                content=content,
                metadata={
                    "name": base_name,
                    "path": path_name,
                },
            )

    def data_source(self) -> str:
        return str(Path(self.local_path) / self.glob_pattern)

    def data_source_provider(self) -> str:
        return "fs"

    @classmethod
    def from_config(cls, config: Dict[str, str]) -> List["FsIngestion"]:
        ingestions = []
        for path, glob_pattern in config.items():
            ingestions.append(cls(local_path=path, glob_pattern=glob_pattern))
        return ingestions
