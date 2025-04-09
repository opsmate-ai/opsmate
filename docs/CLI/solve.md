`opsmate solve` solves a SRE/DevOps oriented task via reasoning.

Unlike most of the state-of-the-art LLMs models (e.g. o1-pro, deepseek R1) that scheming in the background and come back to you 1 minute later, Opsmate reasoning via actively interactive with the environment to gather information and trial and error to find the best solution. We believe short feedback loop is key to solve SRE/DevOps oriented tasks.

## OPTIONS

```
Usage: opsmate solve [OPTIONS] INSTRUCTION

  Solve a problem with the Opsmate.

Options:
  -i, --max-iter INTEGER          Max number of iterations the AI assistant
                                  can reason about  [default: 10]
  -nt, --no-tool-output           Do not print tool outputs
  -a, --answer-only               Print only the answer
  --tool-calls-per-action INTEGER
                                  Number of tool calls per action  [default:
                                  1]
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

### The most basic usage

In the example below, the Opsmate will reason about the problem and come up with a solution, going through the "thought-action-observation" loop.

```bash
opsmate solve "how many cores on the server?"
```

### Using a different model

Like the [`run` command](./run.md), you can use the `--model` option to use a different model.
```bash
opsmate solve "how many cores on the server?" -m grok-2-1212
```

### Increase the number of iterations

You can increase the number of iterations the Opsmate can reason about by using the `--max-iter` option for anything that requires long reasoning. There are a few things to bare in mind though:

- More iterations means more LLM tokens used. As the context window gets progressively larger over iterations, the cost will increase.
- In real-world use cases more iterations doesn't necessarily translate to better results. The common pattern we have observed is that with the current frontier LLMs, 10-15 iterations is the sweet spot. The longer the task, the more "confused" LLM becomes.

```bash
opsmate solve "how many cores on the server?" --max-iter 20
```

### Use various tools

The Opsmate can use various tools to solve the problem. You can see the list of available tools by running the `list-tools` command. To use these tools, you can pass the `--tools` option.

Here is an example of gathering top 10 news from hacker news and write it to a file:

```bash
opsmate solve -na \
  "find me top 10 news on the hacker news with bullet points and write to hn-top-10.md" \
  --tools HtmlToText,FileWrite
...

cat hn-top-10.md
- [Do You Not Like Money?](https://news.ycombinator.com/item?id=43183568) by rbanffy
- [Chile blackout affects 14 regions](https://news.ycombinator.com/item?id=43182892) by impish9208
- [The miserable state of modems and mobile network operators](https://news.ycombinator.com/item?id=43182854) by hasheddan
- [Automattic hit with class action over WP Engine dispute](https://news.ycombinator.com/item?id=43182576) by rpgbr
- [A Radical Proposal for How Mind Emerges from Matter](https://news.ycombinator.com/item?id=43181520) by Hooke
- [Iterlog Coding](https://news.ycombinator.com/item?id=43181610) by snarkconjecture
- [VSC Material Theme](https://news.ycombinator.com/item?id=43178831) by Inityx
- [Fixing Illinois FOIA](https://news.ycombinator.com/item?id=43175628) by mrkurt
- [The XB 70](https://news.ycombinator.com/item?id=43175315) by rbanffy
- [Document Ranking for Complex Problems](https://news.ycombinator.com/item?id=43174910) by noperator
```

### Review and edit commands

Just like the [`run` command](./run.md), you can use the `--review` option to review and edit the commands before execution.

```bash
opsmate solve "how many cores on the server?" -r
```

### Use a different system prompt

You can use the `--system-prompt` or `-s` flag to use a different system prompt.

```bash
opsmate solve "how many cores on the server?" -s "You are a kubernetes SME"
```

### SEE ALSO

- [opsmate run](./run.md)
- [opsmate list-tools](./list-tools.md)
- [opsmate list-models](./list-models.md)
