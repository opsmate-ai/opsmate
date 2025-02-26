`opsmate reset` deletes all the data used by OpsMate. Note that it DOES NOT delete the plugins.

## OPTIONS

```bash
Usage: opsmate reset [OPTIONS]

  Reset the OpsMate.

Options:
  --skip-confirm  Skip confirmation
  --help          Show this message and exit.
```


## EXAMPLES

### Reset the OpsMate

This will reset the database and the vector store. You will be prompted to confirm the reset.

```bash
opsmate reset
```

### Reset the OpsMate without confirmation

This will reset the databases without confirmation.

```bash
opsmate reset --skip-confirm
```
