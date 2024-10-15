import subprocess
from opsmate.libs.core.contexts import (
    Context,
    ContextSpec,
    Metadata,
    Executable,
    ExecShell,
    os_ctx,
)
from opsmate.libs.core.trace import traceit


class GitCurrentBranch(Executable):
    def __call__(self, *args, **kwargs):
        return (
            subprocess.run(["git", "branch", "--show-current"], capture_output=True)
            .stdout.decode()
            .strip()
        )


class GitBranches(Executable):
    def __call__(self, *args, **kwargs):
        return subprocess.run(["git", "branch"], capture_output=True).stdout.decode()


class GitRemote(Executable):
    def __call__(self, *args, **kwargs):
        return subprocess.run(
            ["git", "remote", "-v"], capture_output=True
        ).stdout.decode()


class ExecGit(ExecShell):
    """
    Execute a git command
    """

    @traceit(name="exec_git")
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


git_ctx = Context(
    metadata=Metadata(
        name="git",
        labels={"type": "platform"},
        description="context for git operations",
    ),
    spec=ContextSpec(
        params={},
        contexts=[os_ctx],
        helpers={
            "git_current_branch": GitCurrentBranch(),
            "git_branches": GitBranches(),
            "git_remote": GitRemote(),
        },
        executables=[ExecGit],
        data="""
You are a git CLI specialist.

Here is the current git branch:
<output>
{{ git_current_branch() }}
</output>

Here are the git branches:
<output>
{{ git_branches() }}
</output>

Here is the git remote:
<output>
{{ git_remote() }}
</output>
""",
    ),
)
