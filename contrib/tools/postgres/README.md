# opsmate-tool-postgres

`opsmate-tool-postgres` is a tool for Opsmate that allows you to interact with PostgreSQL databases with the assistance of a LLM.

## Installation

Change directory to this folder and run:
```bash
opsmate install opsmate-tool-postgres
```

To verify the installation, you can run:

```bash
$ opsmate list-tools | grep -i postgres
│ PostgresTool        │ PostgreSQL tool
```


## Usage

First, start the PostgreSQL server using docker-compose:
```bash
docker compose -f fixtures/docker-compose.yml up
```

Then you can test the tool by running:

```bash
opsmate chat \
  --runtime-postgres-password postgres \
  --runtime-postgres-host localhost \
  --runtime-postgres-database ecommerce \
  --runtime-postgres-schema ecommerce \
  --tools PostgresTool
```

## Configurable oOptions

```bash
$ opsmate chat --help | grep -i postgres
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

## Uninstall

```bash
opsmate uninstall -y opsmate-tool-postgres
```
