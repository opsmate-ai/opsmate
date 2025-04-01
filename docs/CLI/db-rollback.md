`db-rollback` is used to rollback the opsmate database to the previous version.

## OPTIONS

```
Usage: opsmate db-rollback [OPTIONS]

  Rollback migrations.

Options:
  -r, --revision TEXT  Revision to downgrade to  [default: -1]
  --help               Show this message and exit.
```

## EXAMPLES

```bash
opsmate db-rollback
```

To rollback to a specific version, run:

```bash
opsmate db-rollback --revision <revision>
```

To list all the versions available, run `opsmate db-revisions`.

## SEE ALSO

- [opsmate db-revisions](./db-revisions.md)
- [opsmate db-migrate](./db-migrate.md)
