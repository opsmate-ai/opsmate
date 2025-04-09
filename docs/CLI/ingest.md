`opsmate ingest` initiate the knowledge ingestion process.

NOTE: The `ingest` command **only** initiates the ingestion process. As the process can be long running, the actual heavy lifting is handled by a `opsmate worker` process.

## OPTIONS

```
Usage: opsmate ingest [OPTIONS]

  Ingest a knowledge base. Notes the ingestion worker needs to be started
  separately with `opsmate worker`.

Options:
  --source TEXT                   Source of the knowledge base
                                  fs:////path/to/kb or
                                  github:///owner/repo[:branch]
  --path TEXT                     Path to the knowledge base  [default: ""]
  --glob TEXT                     Glob to use to find the knowledge base
                                  [default: **/*.md]
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
  --auto-migrate BOOLEAN          Automatically migrate the database to the
                                  latest version  [default: True]
  --help                          Show this message and exit.
```

## EXAMPLES

### Ingest a knowledge base from github

```bash
opsmate ingest \
    --source github:///kubernetes-sigs/kubebuilder:master \
    --path docs/book/src/reference
```

Once you start running `opsmate worker` the ingestion process will start.

## SEE ALSO

- [opsmate worker](./worker.md)
- [opsmate serve](./serve.md)
