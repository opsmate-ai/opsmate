from opsmate.dino.types import ToolCall, PresentationMixin
from pydantic import Field
from typing import ClassVar, Optional
import os
import asyncio
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class Result(BaseModel):
    output: Optional[str] = Field(
        description="The output of the tool call",
        default=None,
    )
    error: Optional[str] = Field(
        description="The error of the tool call",
        default=None,
    )


class GithubCloneAndCD(ToolCall, PresentationMixin):
    """
    Clone a github repository and cd into the directory
    """

    output: Result = Field(
        ..., description="The output of the tool call, DO NOT POPULATE"
    )
    github_domain: ClassVar[str] = "github.com"
    github_token: ClassVar[str] = os.getenv("GITHUB_TOKEN")

    # make this configurable in the future
    working_dir: ClassVar[str] = os.path.join(
        os.getenv("HOME"), ".opsmate", "github_repo"
    )

    repo: str = Field(
        ..., description="The github repository in the format of owner/repo"
    )

    @property
    def clone_url(self) -> str:
        return f"https://{self.github_token}@{self.github_domain}/{self.repo}.git"

    @property
    def repo_path(self) -> str:
        return os.path.join(self.working_dir, self.repo.split("/")[-1])

    async def __call__(self, *args, **kwargs):
        logger.info("cloning repository", repo=self.repo, domain=self.github_domain)

        try:
            os.makedirs(self.working_dir, exist_ok=True)
            process = await asyncio.create_subprocess_shell(
                f"git clone {self.clone_url} {self.repo_path}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=60.0)

            # check the exit code
            if process.returncode != 0:
                raise Exception(f"Failed to clone repository: {stdout.decode()}")

            logger.info("changing directory", path=self.repo_path)
            os.chdir(self.repo_path)

            return Result(output=stdout.decode())
        except asyncio.TimeoutError:
            return Result(error="Failed to clone repository due to timeout")
        except Exception as e:
            return Result(error=f"Failed to clone repository: {e}")

    def markdown(self):
        if self.output.error:
            return f"Failed to clone repository: {self.output.error}"
        else:
            return f"""
## Repo clone success

Repo name: {self.repo}
Repo path: {self.repo_path}
"""
