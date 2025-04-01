`db-migrate` is used to update the sqlite database that powers the opsmate to the latest version. By default it migrates the database to the latest version.

## USAGE

```bash
Usage: opsmate db-migrate [OPTIONS]

  Apply migrations.

Options:
  -r, --revision TEXT  Revision to upgrade to  [default: head]
  --help               Show this message and exit.
```

## EXAMPLES

### Migrating to the latest version

```bash
opsmate db-migrate
```

### Migrating to a specific version

```bash
opsmate db-migrate --revision <revision>
```

To list all the versions available, run `opsmate db-revisions`.

## SEE ALSO

- [opsmate db-revisions](./db-revisions.md)
- [opsmate db-rollback](./db-rollback.md)

## OPTIONS

```
Usage: opsmate db-migrate [OPTIONS]

  Apply migrations.

Options:
  -r, --revision TEXT  Revision to upgrade to  [default: head]
  --help               Show this message and exit.
```
