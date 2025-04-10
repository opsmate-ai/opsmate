from opsmate.runtime.runtime import (
    Runtime,
    RuntimeError,
    register_runtime,
    RuntimeConfig,
)
from pydantic import Field
import asyncio
from typing import Dict, Optional, Any
import psycopg2
import psycopg2.extras
import pandas as pd


class PostgresRuntimeConfig(RuntimeConfig):
    host: str = Field(
        default="localhost",
        alias="RUNTIME_POSTGRES_HOST",
        description="The host of the PostgreSQL server",
    )
    port: int = Field(
        default=5432,
        alias="RUNTIME_POSTGRES_PORT",
        description="The port of the PostgreSQL server",
    )
    user: str = Field(
        default="postgres",
        alias="RUNTIME_POSTGRES_USER",
        description="The user of the PostgreSQL server",
    )
    password: str = Field(
        default="",
        alias="RUNTIME_POSTGRES_PASSWORD",
        description="The password of the PostgreSQL server",
    )
    database: Optional[str] = Field(
        default=None,
        alias="RUNTIME_POSTGRES_DATABASE",
        description="The database of the PostgreSQL server",
    )
    psql_schema: Optional[str] = Field(
        default="public",
        alias="RUNTIME_POSTGRES_SCHEMA",
        description="The schema of the PostgreSQL server",
    )
    timeout: int = Field(
        default=120,
        alias="RUNTIME_POSTGRES_TIMEOUT",
        description="The timeout of the PostgreSQL server in seconds",
    )


@register_runtime("postgres", PostgresRuntimeConfig)
class PostgresRuntime(Runtime):
    """PostgreSQL runtime allows model to execute PostgreSQL queries."""

    def __init__(self, config: PostgresRuntimeConfig = PostgresRuntimeConfig()):
        self._lock = asyncio.Lock()
        self.config = config
        self.connection = None
        self.connected = False

    async def connect(self):
        await self._connect_db()
        await self.run(f"SET statement_timeout = '{self.config.timeout}s'")

    async def _connect_db(self):
        if not self.connected:
            loop = asyncio.get_event_loop()
            try:
                # Execute the blocking connection in a thread pool
                self.connection = await loop.run_in_executor(
                    None,
                    lambda: psycopg2.connect(
                        host=self.config.host,
                        port=self.config.port,
                        user=self.config.user,
                        password=self.config.password,
                        database=self.config.database,
                        options=f"-c search_path={self.config.psql_schema}",
                    ),
                )

                self.connected = True
            except Exception as e:
                raise RuntimeError(f"Failed to connect to PostgreSQL: {e}") from e
        return self.connection

    async def disconnect(self):
        if self.connected and self.connection:
            await asyncio.get_event_loop().run_in_executor(None, self.connection.close)
            self.connected = False
            self.connection = None

    async def os_info(self):
        return await self.run("SELECT version() as version")

    async def whoami(self):
        return await self.run("SELECT current_user as user")

    async def runtime_info(self):
        if self.config.database:
            result = f"postgres runtime connected to {self.config.database} database, schema: {self.config.psql_schema}"
            table_descriptions = await self.describe_tables()
            for table_name, table_description in table_descriptions.items():
                result += f"\n## Table: {table_name}\n"
                result += f"### Schema\n"
                result += table_description.to_markdown()
            return result
        else:
            return "postgres runtime"

    async def describe_tables(self):
        query = f"""
        SELECT
            c.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable
        FROM
            information_schema.columns c
        JOIN
            information_schema.tables t ON c.table_name = t.table_name
        WHERE
            t.table_schema = '{self.config.psql_schema}'
        ORDER BY
            c.table_name,
            c.ordinal_position
        """
        columns = await self.run(query)
        table_descriptions: Dict[str, pd.DataFrame] = {}

        # Group by table_name
        for table_name in {col["table_name"] for col in columns}:
            table_columns = [col for col in columns if col["table_name"] == table_name]
            table_descriptions[table_name] = pd.DataFrame(table_columns)

        return table_descriptions

    async def has_systemd(self):
        return False

    async def run(self, query: str, timeout: float = 30.0):
        async with self._lock:
            try:
                if not self.connected:
                    await self._connect_db()

                loop = asyncio.get_event_loop()

                async def execute_query():
                    # Execute the blocking query in a thread pool
                    with self.connection.cursor(
                        cursor_factory=psycopg2.extras.DictCursor
                    ) as cursor:
                        await loop.run_in_executor(None, cursor.execute, query)
                        if (
                            query.strip()
                            .upper()
                            .startswith(("SELECT", "SHOW", "EXPLAIN"))
                        ):
                            try:
                                rows = await loop.run_in_executor(None, cursor.fetchall)
                                # Convert DictRow objects to plain dictionaries
                                return [dict(row) for row in rows]
                            finally:
                                # commit so that we do not have a stale view in case of transactions happen in separate connections
                                await loop.run_in_executor(None, self.connection.commit)
                        else:
                            await loop.run_in_executor(None, self.connection.commit)
                            return (
                                {
                                    "status": "success",
                                    "rows_affected": cursor.rowcount,
                                },
                            )

                result = await asyncio.wait_for(execute_query(), timeout=timeout)
                return result

            except asyncio.TimeoutError:
                raise RuntimeError(f"Query execution timed out after {timeout} seconds")
            except Exception as e:
                raise RuntimeError(f"Error executing query: {e}") from e
