`opsmate run` executes a command and returns the output.

## OPTIONS

```
Usage: opsmate run [OPTIONS] INSTRUCTION

  Run a task with the Opsmate.

Options:
  -nt, --no-tool-output           Do not print tool outputs
  -no, --no-observation           Do not print observation
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
  --shell-command-runtime TEXT    The runtime to use for the tool call (env:
                                  SHELL_COMMAND_RUNTIME)  [default: local]
  --runtime-k8s-shell TEXT        Set shell_cmd (env: RUNTIME_K8S_SHELL)
                                  [default: /bin/sh]
  --runtime-k8s-container TEXT    Name of the container of the pod, if not
                                  specified, the first container will be used
                                  (env: RUNTIME_K8S_CONTAINER)
  --runtime-k8s-pod TEXT          Set pod_name (env: RUNTIME_K8S_POD)
                                  [default: ""]
  --runtime-k8s-namespace TEXT    Set namespace (env: RUNTIME_K8S_NAMESPACE)
                                  [default: default]
  --runtime-ssh-connect-retries INTEGER
                                  Set connect_retries (env:
                                  RUNTIME_SSH_CONNECT_RETRIES)  [default: 3]
  --runtime-ssh-timeout INTEGER   Set timeout (env: RUNTIME_SSH_TIMEOUT)
                                  [default: 10]
  --runtime-ssh-shell TEXT        Set shell_cmd (env: RUNTIME_SSH_SHELL)
                                  [default: /bin/bash]
  --runtime-ssh-key-file TEXT     Set key_file (env: RUNTIME_SSH_KEY_FILE)
  --runtime-ssh-password TEXT     Set password (env: RUNTIME_SSH_PASSWORD)
  --runtime-ssh-username TEXT     Set username (env: RUNTIME_SSH_USERNAME)
                                  [default: ""]
  --runtime-ssh-port INTEGER      Set port (env: RUNTIME_SSH_PORT)  [default:
                                  22]
  --runtime-ssh-host TEXT         Set host (env: RUNTIME_SSH_HOST)  [default:
                                  ""]
  --runtime-docker-service-name TEXT
                                  Name of the service to run (env:
                                  RUNTIME_DOCKER_SERVICE_NAME)  [default:
                                  default]
  --runtime-docker-compose-file TEXT
                                  Path to the docker compose file (env:
                                  RUNTIME_DOCKER_COMPOSE_FILE)  [default:
                                  docker-compose.yml]
  --runtime-docker-shell TEXT     Set shell_cmd (env: RUNTIME_DOCKER_SHELL)
                                  [default: /bin/bash]
  --runtime-docker-container-name TEXT
                                  Set container_name (env:
                                  RUNTIME_DOCKER_CONTAINER_NAME)  [default:
                                  ""]
  --runtime-local-shell TEXT      Set shell_cmd (env: RUNTIME_LOCAL_SHELL)
                                  [default: /bin/bash]
  -m, --model TEXT                Large language model to use. To list models
                                  available please run the list-models
                                  command.  [default: gpt-4o]
  --tools TEXT                    Comma separated list of tools to use
  -r, --review                    Review and edit commands before execution
  -s, --system-prompt TEXT        System prompt to use
  -c, --context TEXT              Context to be added to the prompt. Run the
                                  list-contexts command to see all the
                                  contexts available.  [default: cli]
  -l, --max-output-length INTEGER
                                  Max length of the output, if the output is
                                  truncated, the tmp file will be printed in
                                  the output  [default: 10000]
  --help                          Show this message and exit.
```

## USAGE

### Simple command
This is the most basic usage of `opsmate run`, it will execute the command based on the natural language instruction.

```bash
opsmate run "what's the linux distribution?"
```

### Execute command with review

By default the command will be executed immediately without any review. You can use the `--review` flag to review the command before execution. Instead of a "yes" or "no" confirmation, you will be able to edit the command before execution.

```bash
opsmate run "what's the linux distribution?" --review
...
Edit the command if needed, then press Enter to execute: !cancel - Cancel the command
Press Enter or edit the command (cat /etc/os-release): cat /etc/os-release | grep '^PRETTY_NAME'
...
```

### Execute command with different model

By default, the model is `gpt-4o`, but you can use a different model for command execution.

```bash
opsmate run "what's the linux distribution?" -m gpt-4o-mini
```

### Execute command with different context

Context is represents a collection of tools and prompts. By default, the context is `cli`, but you can create your own context or use the predefined contexts as shown below.

```bash
opsmate run "how many pods are running in the cluster?" -c k8s
```

### Execute command with different system prompt

You can use the `--system-prompt` or `-s` flag to use a different system prompt.

```bash
opsmate run -s "You are a kubernetes SME" "how many pods are running in the cluster?"
```

### Execute command with different tools

You can also use the `--tools` or `-t` flag to use a different tools. The tools are comma separated values.
The example below shows how to use the `HtmlToText` tool to get top 10 news on the hacker news.

```bash
$ opsmate run -n "find me top 10 news on the hacker news, title only" --tools HtmlToText
2025-02-26 15:14:44 [info     ] adding the plugin directory to the sys path plugin_dir=/home/jingkaihe/.opsmate/plugins
2025-02-26 15:14:44 [info     ] Running on                     instruction=find me top 10 news on the hacker news, title only model=gpt-4o
1. The FFT Strikes Back: An Efficient Alternative to Self-Attention
2. Telescope – an open-source web-based log viewer for logs stored in ClickHouse
3. I Went to SQL Injection Court
4. DeepGEMM: clean and efficient FP8 GEMM kernels with fine-grained scaling
5. The Miserable State of Modems and Mobile Network Operators
6. Hyperspace
7. Material Theme has been pulled from VS Code's marketplace
8. State of emergency declared after blackout plunges most of Chile into darkness
9. Part two of Grant Sanderson's video with Terry Tao on the cosmic distance ladder
10. Launch HN: Browser Use (YC W25) – open-source web agents
```

In the example above we also use the `-n` flag to suppress the tool outputs.

## Pipeline

When the `INSTRUCTION` is `-`, the CLI will read the instruction from the standard input. With this you can chain the commands together.

For example

```bash
cat instructions.txt | opsmate run -
```

Or chaining the `opsmate run` commands together.

```bash
opsmate run -n "how many cores on the machine" | opsmate run - -n -s "print the number * 2 from the text you are given"
2025-02-26 15:23:07 [info     ] adding the plugin directory to the sys path plugin_dir=/home/jingkaihe/.opsmate/plugins
2025-02-26 15:23:10 [info     ] Running on                     instruction=2025-02-26 15:23:07 [info     ] adding the plugin directory to the sys path plugin_dir=/home/jingkaihe/.opsmate/plugins
2025-02-26 15:23:07 [info     ] Running on                     instruction=how many cores on the machine model=gpt-4o
2025-02-26 15:23:08 [info     ] running shell command          command=nproc
8 model=gpt-4o
2025-02-26 15:23:11 [info     ] running shell command          command=echo $((8 * 2))
16
```

### SEE ALSO

- [opsmate solve](./solve.md)
- [opsmate chat](./chat.md)
- [opsmate list-contexts](./list-contexts.md)
- [opsmate list-tools](./list-tools.md)
- [opsmate list-models](./list-models.md)
