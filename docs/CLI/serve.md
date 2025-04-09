`opsmate serve` starts the Opsmate server.

The server has two major functionalities:

1. It offers a web interface for interacting with Opsmate.
2. It includes an experimental REST API server for interacting with Opsmate.

## OPTIONS

```
Usage: opsmate serve [OPTIONS]

  Start the Opsmate server.

Options:
  -h, --host TEXT                 Host to serve on  [default: 0.0.0.0]
  -p, --port INTEGER              Port to serve on  [default: 8080]
  -w, --workers INTEGER           Number of uvicorn workers to serve on
                                  [default: 2]
  --dev                           Run in development mode
  --model TEXT                    Set model (env: OPSMATE_MODEL)  [default:
                                  gpt-4o]
  --context TEXT                  The context to use for the session. Run
                                  `opsmate list-contexts` to see the available
                                  contexts. (env: OPSMATE_CONTEXT)  [default:
                                  k8s]
  --system-prompt TEXT            Set system_prompt (env:
                                  OPSMATE_SYSTEM_PROMPT)  [default: ""]
  --tools TEXT                    Set tools (env: OPSMATE_TOOLS)  [default: Sh
                                  ellCommand,KnowledgeRetrieval,ACITool,HtmlTo
                                  Text,PrometheusTool]
  --token TEXT                    Set token (env: OPSMATE_TOKEN)  [default:
                                  ""]
  --session-name TEXT             Set session_name (env: OPSMATE_SESSION_NAME)
                                  [default: session]
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
  --auto-migrate BOOLEAN          Automatically migrate the database to the
                                  latest version  [default: True]
  --help                          Show this message and exit.
```

## EXAMPLES

### Start the Opsmate server

The command below starts the Opsmate server on the default host and port.

```bash
opsmate serve
```

You can scale up the number of uvicorn workers to handle more requests.

```bash
opsmate serve -w 4
```

In the example above, the server will start 4 uvicorn workers.

### Run in development mode

You can start the server in development mode, which is useful for development purposes.

```bash
opsmate serve --dev
```

### Disable automatic database migration

By default the `serve` command automatically migrates the sqlite database to the latest version. You can disable this behavior by passing `--auto-migrate=[0|False]`.

```bash
opsmate serve --auto-migrate=0
```

## Environment variables

### OPSMATE_SESSION_NAME

The name of the title shown in the web UI, defaults to `session`.

### OPSMATE_TOKEN

This enables token based authentication.

```bash
OPSMATE_TOKEN=<token> opsmate serve
```

Once set you can visit the server via `http://<host>:<port>?token=<token>`. This is NOT a production-grade authn solution and should only be used for development purposes.

For proper authn, authz and TLS termination you should use a production-grade ingress or API Gateway solution.

### OPSMATE_TOOLS

A comma separated list of tools to use, defaults to `ShellCommand,KnowledgeRetrieval`.

### OPSMATE_MODEL

The model used by the AI assistant, defaults to `gpt-4o`.

### OPSMATE_SYSTEM_PROMPT

The system prompt used by the AI assistant, defaults to the `k8s` context.

## SEE ALSO

- [opsmate worker](./worker.md)
- [opsmate chat](./chat.md)
