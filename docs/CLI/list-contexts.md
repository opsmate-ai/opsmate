`opsmate list-contexts` lists all the contexts available.

## OPTIONS

```
Usage: opsmate list-contexts [OPTIONS]

  List all the contexts available.

Options:
  --loglevel TEXT                 Set loglevel (env: OPSMATE_LOGLEVEL)
                                  [default: INFO]
  --categorise BOOLEAN            Whether to categorise the embeddings (env:
                                  OPSMATE_CATEGORISE)  [default: True]
  --reranker-name TEXT            The name of the reranker model (env:
                                  OPSMATE_RERANKER_NAME)  [default: ""]
  --embedding-model-name TEXT     The name of the embedding model (env:
                                  OPSMATE_EMBEDDING_MODEL_NAME)  [default:
                                  text-embedding-ada-002]
  --embedding-registry-name TEXT  The name of the embedding registry (env:
                                  OPSMATE_EMBEDDING_REGISTRY_NAME)  [default:
                                  openai]
  --embeddings-db-path TEXT       The path to the lance db. When s3:// is used
                                  for AWS S3, az:// is used for Azure Blob
                                  Storage, and gs:// is used for Google Cloud
                                  Storage (env: OPSMATE_EMBEDDINGS_DB_PATH)
                                  [default: /root/.opsmate/embeddings]
  --contexts-dir TEXT             Set contexts_dir (env: OPSMATE_CONTEXTS_DIR)
                                  [default: /root/.opsmate/contexts]
  --plugins-dir TEXT              Set plugins_dir (env: OPSMATE_PLUGINS_DIR)
                                  [default: /root/.opsmate/plugins]
  --db-url TEXT                   Set db_url (env: OPSMATE_DB_URL)  [default:
                                  sqlite:////root/.opsmate/opsmate.db]
  --help                          Show this message and exit.
```

## USAGE

### Basic
```bash
opsmate list-contexts

                                    Contexts
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Context   ┃ Description                                                       ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ cli       │ General purpose context for solving problems on the command line. │
│ k8s       │ Kubernetes context for solving problems on Kubernetes.            │
│ terraform │ Terraform context for running Terraform based IaC commands.       │
└───────────┴───────────────────────────────────────────────────────────────────┘
```

### Adding custom contexts
You can also add custom contexts with the help from the opsmate plugin system.

The default location is `$HOME/.opsmate/contexts`. You can change this by setting the `OPSMATE_CONTEXTS_DIR` environment variable.

In the example below we added a `gcloud` context by `$HOME/.opsmate/contexts/gcloud.py` directory:

```python
from opsmate.dino.context import context
from opsmate.plugins import PluginRegistry
import asyncio


@context(
    name="gcloud",
    tools=[
        PluginRegistry.get_tool("ShellCommand"),
        PluginRegistry.get_tool("ACITool"),
        PluginRegistry.get_tool("KnowledgeRetrieval"),
        PluginRegistry.get_tool("HtmlToText"),
    ],
)
async def gcloud_ctx() -> str:
    """GCP SME"""
    tasks = {
        "gcloud_project": __gcloud_project(),
        "gcloud_region": __gcloud_region(),
        "gcloud_projects": __list_gcloud_projects(),
    }
    results = await asyncio.gather(*tasks.values())
    results = dict(zip(tasks.keys(), results))
    """gcloud sme"""

    return f"""
<assistant>
You are a world class SRE who is an expert in gcloud. You are tasked to help with gcloud related problem solving
</assistant>

<useful_info>
gcloud_project: {results["gcloud_project"]}
gcloud_region: {results["gcloud_region"]}
gcloud_projects:
    <gcloud_projects>
    {results["gcloud_projects"]}
    </gcloud_projects>
</useful_info>

<important>
- When you believe the output of `gcloud` command is big, please feel free to use the `tail` command to limit the number of lines.
- If the output contains `<truncated>...</truncated>` it indicates that the output is truncated. If you believe some of the important context are missing, view the tmp file specified using the ACITool to see the missing lines.
- You should also use `format` to limit the number of lines of the output.
</important>
"""


async def __gcloud_project():
    return await __run_cmd("gcloud config get-value project")


async def __gcloud_region():
    return await __run_cmd("gcloud config get-value compute/region")


async def __list_gcloud_projects():
    return await __run_cmd(
        "gcloud projects list --format='value(projectId)' | tail -n 100"
    )


async def __run_cmd(cmd: str):
    process = await asyncio.subprocess.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)

    return stdout.decode().strip()
```

Now if you run `opsmate list-contexts` you will see the `gcloud` context:


```bash
$ opsmate list-contexts
2025-02-28 13:52:15 [info     ] adding the plugin directory to the sys path plugin_dir=/home/jingkaihe/.opsmate/plugins
2025-02-28 13:52:15 [info     ] adding the context directory to the sys path context_dir=/home/jingkaihe/.opsmate/contexts
2025-02-28 13:52:15 [info     ] loading context file           context_path=/home/jingkaihe/.opsmate/contexts/gcloud.py
2025-02-28 13:52:15 [info     ] loaded context file            context_path=/home/jingkaihe/.opsmate/contexts/gcloud.py
               Contexts
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Context   ┃ Description            ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ cli       │ System Admin Assistant │
│ k8s       │ Kubernetes SME         │
│ terraform │ Terraform SME          │
│ gcloud    │ GCP SME                │
└───────────┴────────────────────────┘
```

After adding the plugin, you can use the `gcloud` context via using the `-c` flag:

```bash
$ opsmate solve -c gcloud "what is the current gcp project"
2025-02-28 13:49:00 [info     ] adding the plugin directory to the sys path plugin_dir=/home/jingkaihe/.opsmate/plugins
2025-02-28 13:49:00 [info     ] adding the context directory to the sys path context_dir=/home/jingkaihe/.opsmate/contexts
2025-02-28 13:49:00 [info     ] loading context file           context_path=/home/jingkaihe/.opsmate/contexts/gcloud.py
2025-02-28 13:49:00 [info     ] loaded context file            context_path=/home/jingkaihe/.opsmate/contexts/gcloud.py

                                                               Answer

The current GCP project is "THE-CURRENT-GCP-PROJECT".
```

Note the `--context` flag is available to run, solve and chat commands.

### SEE ALSO

- [opsmate run](./run.md)
- [opsmate solve](./solve.md)
- [opsmate chat](./chat.md)
