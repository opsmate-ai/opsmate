`opsmate serve` starts the Opsmate server.

The server has two major functionalities:

1. It offers a web interface for interacting with Opsmate.
2. It includes an experimental REST API server for interacting with Opsmate.

## OPTIONS

```bash
Usage: opsmate serve [OPTIONS]

  Start the OpsMate server.

Options:
  -h, --host TEXT                 Host to serve on  [default: 0.0.0.0]
  -p, --port INTEGER              Port to serve on  [default: 8080]
  -w, --workers INTEGER           Number of uvicorn workers to serve on
                                  [default: 2]
  --dev                           Run in development mode
  --model TEXT                    Set model (env: OPSMATE_MODEL)  [default:
                                  gpt-4o]
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
  --embeddings-db-path TEXT       The path to the lance db (env:
                                  OPSMATE_EMBEDDINGS_DB_PATH)  [default:
                                  /root/.opsmate/embeddings]
  --contexts-dir TEXT             Set contexts_dir (env: OPSMATE_CONTEXTS_DIR)
                                  [default: /root/.opsmate/contexts]
  --plugins-dir TEXT              Set plugins_dir (env: OPSMATE_PLUGINS_DIR)
                                  [default: /root/.opsmate/plugins]
  --db-url TEXT                   Set db_url (env: OPSMATE_DB_URL)  [default:
                                  sqlite:////root/.opsmate/opsmate.db]
  --auto-migrate BOOLEAN          Automatically migrate the database to the
                                  latest version  [default: True]
  --help                          Show this message and exit.
```


## EXAMPLES

### Start the OpsMate server

The command below starts the OpsMate server on the default host and port.

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
