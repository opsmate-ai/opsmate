`opsmate worker` starts a background worker that handles background tasks, such as chunking knowledge base documents and storing them in the vector database.

This is required for any knowledge ingestion, as the process can be long running and we don't want to run it in the foreground.

## OPTIONS

```
Usage: opsmate worker [OPTIONS]

  Start the Opsmate worker.

Options:
  -w, --workers INTEGER           Number of concurrent background workers
                                  [default: 10]
  -q, --queue TEXT                Queue to use for the worker  [default:
                                  default]
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

### Start the worker

```bash
opsmate worker
```

The command above starts the worker with the default number of workers, which is 10.

### Use custom number of workers

```bash
opsmate worker -w 5
```

The concurrent workers are coroutines which are suitable for IO and network bound tasks.
For any CPU bound tasks you can scale up the number of `opsmate worker` processes via using supervisor program such as `systemd` or [honcho](https://honcho.readthedocs.io/en/latest/).


## SEE ALSO

- [opsmate serve](./serve.md)
- [opsmate ingest](./ingest.md)
