from .k8s import k8s_ctx
from .git import git_ctx
from opsmate.libs.core.contexts import os_ctx, cli_ctx, react_ctx

available_contexts = [k8s_ctx, os_ctx, cli_ctx, react_ctx, git_ctx]
