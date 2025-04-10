import pytest
import asyncio
from contrib.tools.postgres.postgres.runtime import (
    PostgresRuntime,
    PostgresRuntimeConfig,
)
from contextlib import asynccontextmanager
import os
import subprocess
import structlog

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def postgres_runtime(
    password="postgres",
):
    # Use the fixed docker-compose file in fixtures directory
    compose_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "fixtures", "docker-compose.yml"
    )
    logger.info("PostgreSQL runtime compose file", compose_file=compose_file)

    # start the test postgres server
    subprocess.run(f"docker compose -f {compose_file} up -d", shell=True, check=False)

    try:

        async def await_postgres_server():
            max_retries = 20
            retry_interval = 2
            for i in range(max_retries):
                try:
                    logger.info("Waiting for PostgreSQL server to start", retry=i)
                    # First check if the container is healthy
                    subprocess.run(
                        f"docker compose -f {compose_file} exec postgres-server pg_isready -U postgres",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                    # Then try to actually connect and run a query
                    subprocess.run(
                        f"docker compose -f {compose_file} exec postgres-server psql -U postgres -c 'SELECT 1'",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                    break
                except subprocess.CalledProcessError:
                    if i == max_retries - 1:
                        pytest.fail("PostgreSQL server failed to start")
                    await asyncio.sleep(retry_interval)

        await await_postgres_server()

        runtime_config = PostgresRuntimeConfig(
            RUNTIME_POSTGRES_HOST="localhost",
            RUNTIME_POSTGRES_PORT=5432,
            RUNTIME_POSTGRES_USER="postgres",
            RUNTIME_POSTGRES_PASSWORD=password,
            RUNTIME_POSTGRES_DATABASE="testdb",
        )
        runtime = PostgresRuntime(runtime_config)

        await runtime.connect()
        yield runtime_config, runtime
    finally:
        try:
            await runtime.disconnect()

            subprocess.run(
                f"docker compose -f {compose_file} down", shell=True, check=False
            )
        except Exception as e:
            logger.error("Failed to stop PostgreSQL runtime", error=e)


@pytest.mark.serial
class TestPostgresRuntime:
    @pytest.mark.asyncio
    async def test_postgres_runtime(self):
        async with postgres_runtime() as (runtime_config, runtime):
            assert runtime.connected is True

            # test the runtime info
            runtime_info = await runtime.runtime_info()
            assert "postgres runtime" in runtime_info

            # test the os info
            os_info = await runtime.os_info()
            assert len(os_info) == 1
            assert "version" in os_info[0]
            assert "PostgreSQL" in os_info[0]["version"]

            has_systemd = await runtime.has_systemd()
            assert has_systemd is False

            # test the whoami
            whoami = await runtime.whoami()
            assert len(whoami) == 1
            assert "user" in whoami[0]
            assert "postgres" in whoami[0]["user"]

            result = await runtime.run("SELECT * FROM test")
            assert result == [{"id": 1, "name": "test"}]

            # Connect to the pre-created test database
            runtime_config2 = PostgresRuntimeConfig(
                RUNTIME_POSTGRES_HOST=runtime_config.host,
                RUNTIME_POSTGRES_PORT=runtime_config.port,
                RUNTIME_POSTGRES_USER=runtime_config.user,
                RUNTIME_POSTGRES_PASSWORD=runtime_config.password,
                RUNTIME_POSTGRES_DATABASE=runtime_config.database,
            )
            runtime2 = PostgresRuntime(runtime_config2)
            await runtime2.connect()

            # Insert a new row
            await runtime2.run("INSERT INTO test (name) VALUES ('test2')")
            result = await runtime2.run("SELECT * FROM test")
            assert [{"id": 1, "name": "test"}, {"id": 2, "name": "test2"}] == result

            # make sure the view of the runtime is updated
            result = await runtime.run("SELECT * FROM test")
            assert result == [{"id": 1, "name": "test"}, {"id": 2, "name": "test2"}]
