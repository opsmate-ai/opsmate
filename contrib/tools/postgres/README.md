# opsmate-tool-postgres

`opsmate-tool-postgres` is a tool for Opsmate that allows you to interact with PostgreSQL databases with the assistance of a LLM.

## Should I use this tool?

:warning: This is an early prototype and the protocol is yet to be finalized. :warning:

Here is the guide to help you to make decisions about whether you should use this tool at the moment:

| Situation | Recommendation |
|-----------|----------|
| I am not sure if this tool is mature enough for my use case | Don't use it |
| I want this tool to perform all the production db administration tasks for me | Absolutely not |
| There is a pressing production issue that needs to be resolved urgently, this postgres plugin might be useful | Seriously NO |
| I really want to use this tool but I'm worried about PII and data privacy implications | Don't use it |
| I have a non-production database and I want to test this tool | Maybe |

## Installation

Change directory to this folder and run:
```bash
opsmate install opsmate-tool-postgres
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

## Implementation Details

The tool is implemented in the `postgres/tool.py` file.

The tool uses the `PostgresRuntime` class to connect to the PostgreSQL server, which implements the `Runtime` interface. It is implemented in the `postgres/runtime.py` file.

In the [pyproject.toml](./pyproject.toml) file you can find the entry points for the tool and the runtime:

```toml
[project.entry-points."opsmate.tools"]
tool = "postgres.tool:PostgresTool"

[project.entry-points."opsmate.runtime.runtimes"]
runtime = "postgres.runtime:PostgresRuntime"
```

This is to make sure that the tools are "autodiscovered" by Opsmate on startup. To verify this you can run the following commands:

```bash
# to verify the postgres tool is autodiscovered
opsmate list-tools | grep -i postgres
│ PostgresTool           │ PostgreSQL tool
```

```bash
# to verify the postgres runtime is autodiscovered
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
