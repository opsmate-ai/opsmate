`opsmate ingest` initiate the knowledge ingestion process.

NOTE: The `ingest` command **only** initiates the ingestion process. As the process can be long running, the actual heavy lifting is handled by a `opsmate worker` process.

## OPTIONS

```bash
Usage: opsmate ingest [OPTIONS]

  Ingest a knowledge base. Notes the ingestion worker needs to be started
  separately with `opsmate worker`.

Options:
  --source TEXT           Source of the knowledge base fs:////path/to/kb or
                          github:///owner/repo[:branch]
  --path TEXT             Path to the knowledge base
  --glob TEXT             Glob to use to find the knowledge base  [default:
                          **/*.md]
  --auto-migrate BOOLEAN  Automatically migrate the database to the latest
                          version  [default: True]
  --help                  Show this message and exit.
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
