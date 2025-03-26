Opsmate uses [LanceDB](https://lancedb.github.io/lancedb/) to store knowledge bases. By default we store the knowledge base in the local filesystem, default at `~/.opsmate/embeddings`, and configures as `OPSMATE_EMBEDDINGS_DB_PATH`.

The full pros and cons of storage considerations are covered in the [LanceDB Storage `documentation](https://lancedb.github.io/lancedb/concepts/storage).

Currently In addition to local filesystem, Opsmate officially supports AWS S3 and Azure Blob Storage based cloud storage. That being said we expect other approaches suggested by LanceDB to work as well.


## Prerequisites

- You must have already provisioned the cloud storage bucket.
- You must have read-only+ access to the cloud storage bucket.

## How to use cloud storage for embeddings storage

=== "Environment Variable"
    Simply set the `OPSMATE_EMBEDDINGS_DB_PATH` environment variable to the cloud storage path.
    ```bash
    # AWS S3
    OPSMATE_EMBEDDINGS_DB_PATH=s3://bucket/path
    # Azure Blob Storage
    OPSMATE_EMBEDDINGS_DB_PATH=az://bucket/path
    # Google Cloud Storage
    OPSMATE_EMBEDDINGS_DB_PATH=gs://bucket/path
    ```

=== "CLI"
    Use the `--embeddings-db-path` flag to specify the cloud storage path.
    ```bash
    # AWS S3
    opsmate ingest --embeddings-db-path=s3://bucket/path
    # Azure Blob Storage
    opsmate ingest --embeddings-db-path=az://bucket/path
    # Google Cloud Storage
    opsmate ingest --embeddings-db-path=gs://bucket/path
    ```

=== "Config File"
    Alternatively you can also set the config in `~/.opsmate/config.yaml`:
    ```yaml
    # AWS S3
    OPSMATE_EMBEDDINGS_DB_PATH: s3://bucket/path
    # Azure Blob Storage
    OPSMATE_EMBEDDINGS_DB_PATH: az://bucket/path
    # Google Cloud Storage
    OPSMATE_EMBEDDINGS_DB_PATH: gs://bucket/path
    ```

Please refer to the [LanceDB Configure Cloud Storage](https://lancedb.github.io/lancedb/guides/storage/) for more details.
