from typing import AsyncGenerator
from .base import BaseIngestion, Document
from pydantic import Field
from glob import glob
from os import path
from pathlib import Path
from typing import Dict, List
from hashlib import sha256


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
            full_path = path.abspath(filename)
            sha = sha256(content.encode("utf-8")).hexdigest()
            yield Document(
                data_provider=self.data_source_provider(),
                data_source=self.data_source(),
                content=content,
                metadata={
                    "name": base_name,
                    "path": full_path,
                    "sha": sha,
                },
            )

    def data_source(self) -> str:
        return str(Path(self.local_path) / self.glob_pattern)

    def data_source_provider(self) -> str:
        return "fs"

    @classmethod
    def from_configmap(cls, config: Dict[str, str]) -> List["FsIngestion"]:
        ingestions = []
        for path, glob_pattern in config.items():
            ingestions.append(cls(local_path=path, glob_pattern=glob_pattern))
        return ingestions
