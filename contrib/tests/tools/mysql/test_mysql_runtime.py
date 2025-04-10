import pytest
import asyncio
from contrib.tools.mysql.mysql.runtime import MySQLRuntime, MySQLRuntimeConfig
from contextlib import asynccontextmanager
import os
import subprocess
import structlog

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def mysql_runtime(
    password="my-secret-pw",
):
    # Use the fixed docker-compose file in fixtures directory
    compose_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "fixtures", "docker-compose.yml"
    )
    logger.info("MySQL runtime compose file", compose_file=compose_file)

    # start the test mysql server
    subprocess.run(f"docker compose -f {compose_file} up -d", shell=True, check=False)

    try:

        async def await_mysql_server():
            max_retries = 20
            retry_interval = 2
            for i in range(max_retries):
                try:
                    logger.info("Waiting for MySQL server to start", retry=i)
                    # First check if the container is healthy
                    subprocess.run(
                        f"docker compose -f {compose_file} exec mysql-server mysqladmin ping -h localhost -u root -p{password}",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                    # Then try to actually connect and run a query
                    subprocess.run(
                        f"docker compose -f {compose_file} exec mysql-server mysql -h localhost -u root -p{password} -e 'SELECT 1'",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                    break
                except subprocess.CalledProcessError:
                    if i == max_retries - 1:
                        pytest.fail("MySQL server failed to start")
                    await asyncio.sleep(retry_interval)

        await await_mysql_server()

        runtime_config = MySQLRuntimeConfig(
            RUNTIME_MYSQL_HOST="localhost",
            RUNTIME_MYSQL_PORT=3306,
            RUNTIME_MYSQL_USER="root",
            RUNTIME_MYSQL_PASSWORD=password,
        )
        runtime = MySQLRuntime(runtime_config)

        await runtime.connect()
        yield runtime_config, runtime
    finally:
        try:
            await runtime.disconnect()

            subprocess.run(
                f"docker compose -f {compose_file} down", shell=True, check=False
            )
        except Exception as e:
            logger.error("Failed to stop MySQL runtime", error=e)


@pytest.mark.serial
class TestMySQLRuntime:
    @pytest.mark.asyncio
    async def test_mysql_runtime(self):
        async with mysql_runtime() as (runtime_config, runtime):
            assert runtime.connected is True

            # test the runtime info
            runtime_info = await runtime.runtime_info()
            assert "mysql runtime" in runtime_info

            # test the os info
            os_info = await runtime.os_info()
            assert [{"version": "9.2.0"}] == os_info

            has_systemd = await runtime.has_systemd()
            assert has_systemd is False

            # test the whoami
            whoami = await runtime.whoami()
            assert [{"user": "root@%"}] == whoami

            # create a table
            await runtime.run("CREATE DATABASE test")
            await runtime.run("USE test")
            await runtime.run("CREATE TABLE test (id INT)")
            await runtime.run("INSERT INTO test (id) VALUES (1)")
            result = await runtime.run("SELECT * FROM test")
            assert [{"id": 1}] == result

            runtime_config2 = MySQLRuntimeConfig(
                RUNTIME_MYSQL_HOST=runtime_config.host,
                RUNTIME_MYSQL_PORT=runtime_config.port,
                RUNTIME_MYSQL_USER=runtime_config.user,
                RUNTIME_MYSQL_PASSWORD=runtime_config.password,
                RUNTIME_MYSQL_DATABASE="test",
            )
            runtime2 = MySQLRuntime(runtime_config2)
            await runtime2.connect()
            result = await runtime2.run("SELECT * FROM test")
            assert [{"id": 1}] == result

            # insert a new row
            await runtime2.run("INSERT INTO test (id) VALUES (2)")
            result = await runtime2.run("SELECT * FROM test")
            assert [{"id": 1}, {"id": 2}] == result

            # the first runtime has the same view
            result = await runtime.run("SELECT * FROM test")
            assert [{"id": 1}, {"id": 2}] == result
