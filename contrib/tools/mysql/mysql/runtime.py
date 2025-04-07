from opsmate.runtime.runtime import (
    Runtime,
    RuntimeError,
    register_runtime,
    RuntimeConfig,
)
from pydantic import Field
import asyncio
from typing import Dict, Optional, Any
import pymysql
import pymysql.cursors
import pandas as pd


class MySQLRuntimeConfig(RuntimeConfig):
    host: str = Field(
        default="localhost",
        alias="RUNTIME_MYSQL_HOST",
        description="The host of the MySQL server",
    )
    port: int = Field(
        default=3306,
        alias="RUNTIME_MYSQL_PORT",
        description="The port of the MySQL server",
    )
    user: str = Field(
        default="root",
        alias="RUNTIME_MYSQL_USER",
        description="The user of the MySQL server",
    )
    password: str = Field(
        default="",
        alias="RUNTIME_MYSQL_PASSWORD",
        description="The password of the MySQL server",
    )
    database: Optional[str] = Field(
        default=None,
        alias="RUNTIME_MYSQL_DATABASE",
        description="The database of the MySQL server",
    )
    charset: str = Field(
        default="utf8mb4",
        alias="RUNTIME_MYSQL_CHARSET",
        description="The charset of the MySQL server",
    )
    timeout: int = Field(
        default=120,
        alias="RUNTIME_MYSQL_TIMEOUT",
        description="The timeout of the MySQL server",
    )


@register_runtime("mysql", MySQLRuntimeConfig)
class MySQLRuntime(Runtime):
    """MySQL runtime allows model to execute MySQL queries."""

    def __init__(self, config: MySQLRuntimeConfig = MySQLRuntimeConfig()):
        self._lock = asyncio.Lock()
        self.config = config
        self.connection = None
        self.connected = False

    async def connect(self):
        await self._connect_db()

    async def _connect_db(self):
        if not self.connected:
            loop = asyncio.get_event_loop()
            try:
                # Execute the blocking connection in a thread pool
                self.connection = await loop.run_in_executor(
                    None,
                    lambda: pymysql.connect(
                        host=self.config.host,
                        port=self.config.port,
                        user=self.config.user,
                        password=self.config.password,
                        database=self.config.database,
                        charset=self.config.charset,
                        cursorclass=pymysql.cursors.DictCursor,
                        connect_timeout=self.config.timeout,
                    ),
                )
                self.connected = True
            except Exception as e:
                raise RuntimeError(f"Failed to connect to MySQL: {e}") from e
        return self.connection

    async def disconnect(self):
        if self.connected and self.connection:
            await asyncio.get_event_loop().run_in_executor(None, self.connection.close)
            self.connected = False
            self.connection = None

    async def os_info(self):
        return await self.run("SELECT VERSION() as version")

    async def whoami(self):
        return await self.run("SELECT CURRENT_USER() as user")

    async def runtime_info(self):
        if self.config.database:
            result = f"mysql runtime connected to {self.config.database} database"
            table_descriptions = await self.describe_tables()
            for table_name, table_description in table_descriptions.items():
                result += f"\n## Table:{table_name}\n"
                result += f"### Schema\n"
                result += table_description.to_markdown()
            return result

        else:
            return "mysql runtime"

    async def describe_tables(self):
        tables = await self.run("SHOW TABLES")
        table_names = [table["Tables_in_" + self.config.database] for table in tables]
        table_descriptions: Dict[str, pd.DataFrame] = {}
        for table_name in table_names:
            table_description = await self.run(f"DESCRIBE {table_name}")
            table_descriptions[table_name] = pd.DataFrame(table_description)
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
                    with self.connection.cursor() as cursor:
                        await loop.run_in_executor(None, cursor.execute, query)
                        if (
                            query.strip()
                            .upper()
                            .startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN"))
                        ):
                            try:
                                return await loop.run_in_executor(None, cursor.fetchall)
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
