`opsmate schedule-embeddings-reindex` schedules a task to reindex the embeddings. Note that this command only schedules the task.To reindex the embeddings, the `opsmate worker` process needs to be running.

Opsmate uses LanceDB to store the embedding vectors for semantic search and full text search. By default LanceDB [does not support](https://lancedb.github.io/lancedb/concepts/data_management/) incremental indexing. This `schedule-embeddings-reindex` command schedules a task to reindex the embeddings. Once the reindex task is scheduled, the task will be run periodically by default every 30 seconds.

## OPTIONS

```
Usage: opsmate schedule-embeddings-reindex [OPTIONS]

  Schedule the reindex embeddings table task. It will purge all the reindex
  tasks before scheduling the new one. After schedule the reindex task will be
  run periodically every 30 seconds.

Options:
  -i, --interval-seconds INTEGER  Interval seconds to run the reindex task
                                  [default: 30]
  -nw, --no-wait-for-completion   Do not wait for the reindex task to complete
                                  before scheduling the next one
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

## USAGE

### Basic

Here is the most basic usage:

```bash
opsmate schedule-embeddings-reindex
```

It will wait for the reindex task to complete before scheduling the next one.

### Interval

Note that the default interval between reindex tasks is 30 seconds. You can change it by using the `--interval-seconds` option.

```bash
opsmate schedule-embeddings-reindex -i 60
```

This will schedule a reindex task to run every 60 seconds.

### No wait for completion

You can do not wait for the reindex task to complete before scheduling the next one by using the `--no-wait-for-completion` option.

```bash
opsmate schedule-embeddings-reindex -nw
```

This is useful when your existing reindex task is stalled but you want to schedule a new one without tidying up the existing one. In most cases you should not use this option.

## SEE ALSO

- [opsmate worker](./worker.md)
- [opsmate ingest](./ingest.md)
