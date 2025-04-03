# MySQL Tool

This is an early prototype of a MySQL tool for OpsMate.

## Installation

```bash
opsmate install opsmate-tools-mysql
```

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
opsmate install -e .
```

## Usage

First, start the MySQL server using docker-compose:
Note we have a x-for-pet database schema and sample data in the `fixtures/mydb.sql` file.
```bash
docker compose -f fixtures/docker-compose.yml up
```

Then you can test the tool by running:

```bash
opsmate chat --runtime mysql \
  --runtime-mysql-password my-secret-pw \
  --runtime-mysql-host localhost \
  --tools MySQLTool
```
