PostgresTool is a tool that allows you to interact with PostgreSQL databases.

## Installation

The PostgresTool is not pre-installed with Opsmate. You need to install it explicitly:

```bash
opsmate install opsmate-tool-postgres
```

To verify the installation, you can run:

```bash
$ opsmate list-tools | grep -i postgres
│ PostgresTool        │ PostgreSQL tool
```

The command line options will be added to the `opsmate [run|solve|chat|serve]` commands:

```bash
# to verify the postgres runtime is autodiscovered
opsmate chat --help | grep -i postgres
  --postgres-tool-runtime TEXT    The runtime to use for the tool call (env:
                                  POSTGRES_TOOL_RUNTIME)  [default: postgres]
  --runtime-postgres-timeout INTEGER
                                  The timeout of the PostgreSQL server in
                                  seconds (env: RUNTIME_POSTGRES_TIMEOUT)
  --runtime-postgres-schema TEXT  The schema of the PostgreSQL server (env:
                                  RUNTIME_POSTGRES_SCHEMA)  [default: public]
  --runtime-postgres-database TEXT
                                  The database of the PostgreSQL server (env:
                                  RUNTIME_POSTGRES_DATABASE)
  --runtime-postgres-password TEXT
                                  The password of the PostgreSQL server (env:
                                  RUNTIME_POSTGRES_PASSWORD)  [default: ""]
  --runtime-postgres-user TEXT    The user of the PostgreSQL server (env:
                                  RUNTIME_POSTGRES_USER)  [default: postgres]
  --runtime-postgres-port INTEGER
                                  The port of the PostgreSQL server (env:
                                  RUNTIME_POSTGRES_PORT)  [default: 5432]
  --runtime-postgres-host TEXT    The host of the PostgreSQL server (env:
                                  RUNTIME_POSTGRES_HOST)  [default: localhost]
```

## Usage

Similar to the [MySQLTool](./mysql.md), you can interact with the Postgres database by running:

```bash
opsmate chat \
  --runtime-postgres-password postgres \
  --runtime-postgres-host localhost \
  --runtime-postgres-database <your-database> \
  --runtime-postgres-schema <your-schema> \
  --tools PostgresTool
```

## Uninstall

```bash
opsmate uninstall -y opsmate-tool-postgres
```
