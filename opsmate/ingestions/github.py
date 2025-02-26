from typing import AsyncGenerator, Optional
from .base import BaseIngestion, Document
from pydantic import Field, model_validator
import os
import httpx
import asyncio
import base64
import fnmatch
from typing import Dict, List


class GithubIngestion(BaseIngestion):
    repo: str = Field(..., description="The repository in the format of owner/repo")
    github_token: Optional[str] = Field(
        description="The GitHub token to use", default=None
    )
    github_api_url: str = Field(
        "https://api.github.com", description="The GitHub API URL"
    )
    branch: str = Field("main", description="The branch to ingest")
    path: str = Field("", description="The path to ingest")
    client: Optional[httpx.AsyncClient] = Field(
        description="The HTTP client to use", default_factory=httpx.AsyncClient
    )
    concurrency: int = Field(10, description="The concurrency to use")
    glob: str = Field("", description="The glob patternto use")

    @model_validator(mode="before")
    @classmethod
    def validate_github_token(cls, v):
        token = v.get("github_token")
        if not token:
            token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GitHub token is required")
        v["github_token"] = token
        return v

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "opsmate / 0.1.0 (https://github.com/jingkaihe/opsmate)",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_files(self) -> AsyncGenerator[str, None]:
        # https://api.github.com/repos/OWNER/REPO/git/trees/TREE_SHA
        url = f"{self.github_api_url}/repos/{self.repo}/git/trees/{self.branch}?recursive=1"
        response = await self.client.get(url, headers=self.headers)
        response.raise_for_status()

        tree = response.json().get("tree")
        for item in tree:
            if item.get("type") == "blob":
                path = item.get("path")
                if self.path != "" and not path.startswith(self.path):
                    continue
                if self.glob and not fnmatch.fnmatch(f"./{path}", self.glob):
                    continue
                yield path

    async def get_file_with_metadata(self, file_path: str) -> Dict[str, str]:
        # https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28
        url = f"{self.github_api_url}/repos/{self.repo}/contents/{file_path}"

        response = await self.client.get(url, headers=self.headers)
        response.raise_for_status()
        body = response.json()
        content_encoded = body.get("content")
        return {
            "content": base64.b64decode(content_encoded).decode("utf-8"),
            "html_url": body.get("html_url"),
            "sha": body.get("sha"),
        }

    async def load(self) -> AsyncGenerator[Document, None]:
        # semaphore to limit the number of concurrent requests
        semaphore = asyncio.Semaphore(self.concurrency)

        async def process_file(file: str) -> Document:
            async with semaphore:
                content_with_metadata = await self.get_file_with_metadata(file)
                return Document(
                    data_provider=self.data_source_provider(),
                    data_source=self.data_source(),
                    content=content_with_metadata.get("content"),
                    metadata={
                        "path": file,
                        "repo": self.repo,
                        "branch": self.branch,
                        "source": content_with_metadata.get("html_url"),
                        "sha": content_with_metadata.get("sha"),
                    },
                )

        tasks = [
            asyncio.create_task(process_file(file)) async for file in self.get_files()
        ]

        # Process completed tasks
        for task in asyncio.as_completed(tasks):
            yield await task

    def data_source(self) -> str:
        return self.repo

    def data_source_provider(self) -> str:
        return "github"

    @classmethod
    def from_configmap(cls, config: Dict[str, str]) -> List["GithubIngestion"]:
        ingestions = []
        for repo, glob_pattern in config.items():
            maybe_branch = repo.split(":")
            if len(maybe_branch) == 2:
                repo, branch = maybe_branch
            else:
                repo, branch = repo, "main"
            ingestions.append(cls(repo=repo, glob=glob_pattern, branch=branch))
        return ingestions
