from opsmate.dino.types import ToolCall
from pydantic import Field
from typing import ClassVar, Optional
import os
import asyncio
import structlog

logger = structlog.get_logger(__name__)


class GithubCloneAndCD(ToolCall):
    """
    Clone a github repository and cd into the directory
    """

    output: str = Field(..., description="The output of the tool call, DO NOT POPULATE")
    github_domain: ClassVar[str] = "github.com"
    github_token: ClassVar[str] = os.getenv("GITHUB_TOKEN")

    repo: str = Field(
        ..., description="The github repository in the format of owner/repo"
    )

    @property
    def clone_url(self) -> str:
        return f"https://{self.github_token}@{self.github_domain}/{self.repo}.git"

    async def __call__(self, *args, **kwargs):
        logger.info("cloning repository", repo=self.repo, domain=self.github_domain)

        try:
            process = await asyncio.create_subprocess_shell(
                f"git clone {self.clone_url}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=60.0)

            # check the exit code
            if process.returncode != 0:
                raise Exception(f"Failed to clone repository: {stdout.decode()}")

            repo_path = self.repo.split("/")[-1]
            logger.info("changing directory", path=repo_path)
            os.chdir(repo_path)

            return stdout.decode()
        except asyncio.TimeoutError:
            return "Failed to clone repository due to timeout"
        except Exception as e:
            return f"Failed to clone repository: {e}"
