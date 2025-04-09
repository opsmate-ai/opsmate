`opsmate chat` allows you to use the Opsmate in an interactive chat interface.

## OPTIONS

```
Usage: opsmate chat [OPTIONS]

  Chat with the Opsmate.

Options:
  -i, --max-iter INTEGER          Max number of iterations the AI assistant
                                  can reason about  [default: 10]
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

### Basic

Herer is the most basic usage of the `opsmate chat` command:

```bash
Opsmate> Howdy! How can I help you?

Commands:

!clear - Clear the chat history
!exit - Exit the chat
!help - Show this message
```

### With a system prompt

You can use a system prompt with the `opsmate chat` command by using the `-s` or `--system-prompt` flag.

```bash
opsmate chat -s "you are a rabbit"
2025-02-26 18:10:12 [info     ] adding the plugin directory to the sys path plugin_dir=/home/jingkaihe/.opsmate/plugins
Opsmate> Howdy! How can I help you?

Commands:

!clear - Clear the chat history
!exit - Exit the chat
!help - Show this message

You> who are you

Answer

I am a rabbit, here to assist you with your queries and tasks.
You>
```
