from typing import AsyncGenerator
from .base import BaseIngestion, Document
from pydantic import BaseModel, Field
from glob import glob
from os import path


class FsIngestion(BaseIngestion):
    def __init__(
        self,
        *args,
        local_path: str,
        glob_pattern: str = "**/*",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.local_path = local_path
        self.glob_pattern = glob_pattern

    async def load(self) -> AsyncGenerator[Document, None]:
        glob_pattern = path.join(self.local_path, self.glob_pattern)
        files = glob(glob_pattern, recursive=True)
        for filename in files:
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
