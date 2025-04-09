# opsmate-tool-mysql

`opsmate-tool-mysql` is a tool for Opsmate that allows you to interact with MySQL databases with the assistance of a LLM.

## Should I use this tool?

:warning: This is an early prototype and the protocol is yet to be finalized. :warning:

Here is the guide to help you to make decisions about whether you should use this tool at the moment:

| Situation | Recommendation |
|-----------|----------|
| I am not sure if this tool is mature enough for my use case | Don't use it |
| I want this tool to perform all the production db administration tasks for me | Absolutely not |
| There is a pressing production issue that needs to be resolved urgently, this mysql plugin might be useful | Seriously NO |
| I really want to use this tool but I'm worried about PII and data privacy implications | Don't use it |
| I have a non-production database and I want to test this tool | Maybe |

## Installation

Change directory to this folder and run:
```bash
opsmate install opsmate-tool-mysql
```

## Usage

First, start the MySQL server using docker-compose:
Note we have a x-for-pet database schema and sample data in the `fixtures/mydb.sql` file.
```bash
docker compose -f fixtures/docker-compose.yml up
```

Then you can test the tool by running:

```bash
opsmate chat\
  --runtime-mysql-password my-secret-pw \
  --runtime-mysql-host localhost \
  --tools MySQLTool
```

## Implementation Details

The tool is implemented in the `mysql/tool.py` file.

The tool uses the `MySQLRuntime` class to connect to the MySQL server, which is implements the `Runtime` interface. It is implemented in the `mysql/runtime.py` file.

In the [pyproject.toml](./pyproject.toml) file you can find the entry points for the tool and the runtime:

```toml
[project.entry-points."opsmate.tools"]
tool = "mysql.tool:MySQLTool"

[project.entry-points."opsmate.runtime.runtimes"]
runtime = "mysql.runtime:MySQLRuntime"
```

This is to make sure that the tools are "autodiscovered" by Opsmate on startup. To verify this you can run the following commands:

```bash
# to verify the mysql tool is autodiscovered
opsmate list-tools | grep -i mysql
│ MySQLTool           │ MySQL tool
```

```bash
# to verify the mysql runtime is autodiscovered
opsmate chat --help | grep -i mysql
  --runtime-mysql-timeout INTEGER
                                  The timeout of the MySQL server (env:
                                  RUNTIME_MYSQL_TIMEOUT)  [default: 120]
  --runtime-mysql-charset TEXT    The charset of the MySQL server (env:
                                  RUNTIME_MYSQL_CHARSET)  [default: utf8mb4]
  --runtime-mysql-database TEXT   The database of the MySQL server (env:
                                  RUNTIME_MYSQL_DATABASE)
  --runtime-mysql-password TEXT   The password of the MySQL server (env:
                                  RUNTIME_MYSQL_PASSWORD)  [default: ""]
  --runtime-mysql-user TEXT       The user of the MySQL server (env:
                                  RUNTIME_MYSQL_USER)  [default: root]
  --runtime-mysql-port INTEGER    The port of the MySQL server (env:
                                  RUNTIME_MYSQL_PORT)  [default: 3306]
  --runtime-mysql-host TEXT       The host of the MySQL server (env:
                                  RUNTIME_MYSQL_HOST)  [default: localhost]
```

## Uninstall

```bash
opsmate uninstall -y opsmate-tool-mysql
```
