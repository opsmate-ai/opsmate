`opsmate worker` starts a background worker that handles background tasks, such as chunking knowledge base documents and storing them in the vector database.

This is required for any knowledge ingestion, as the process can be long running and we don't want to run it in the foreground.

## OPTIONS

```bash
Usage: opsmate worker [OPTIONS]

  Start the OpsMate worker.

Options:
  -w, --workers INTEGER   Number of concurrent background workers  [default:
                          10]
  --auto-migrate BOOLEAN  Automatically migrate the database to the latest
                          version  [default: True]
  --help                  Show this message and exit.
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
