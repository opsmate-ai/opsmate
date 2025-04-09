`opsmate reset` deletes all the data used by Opsmate. Note that it DOES NOT delete the plugins.

## OPTIONS

```
Usage: opsmate reset [OPTIONS]

  Reset the Opsmate database and embeddings db. Note that if the database is
  using litestream it will not be reset. Same applies to the embeddings db, if
  the embedding db is using GCS, S3 or Azure Blob Storage, it will not be
  reset.

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
  --skip-confirm                  Skip confirmation
  --help                          Show this message and exit.
```

## EXAMPLES

### Reset the Opsmate

This will reset the database and the vector store. You will be prompted to confirm the reset.

```bash
opsmate reset
```

### Reset the Opsmate without confirmation

This will reset the databases without confirmation.

```bash
opsmate reset --skip-confirm
```
