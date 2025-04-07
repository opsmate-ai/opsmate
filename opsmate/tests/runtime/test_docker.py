import pytest
import asyncio
from opsmate.runtime import DockerRuntime, RuntimeError, Runtime
from opsmate.runtime.docker import DockerRuntimeConfig
from contextlib import asynccontextmanager
import os
from tempfile import NamedTemporaryFile
import subprocess
from subprocess import check_call as co


@asynccontextmanager
async def docker_runtime(
    compose_file="docker-compose.yml",
    service_name="default",
    container_name="",
    shell_cmd="/bin/sh",
    envvars={},
):
    if container_name != "":
        runtime = DockerRuntime(
            DockerRuntimeConfig(
                container_name=container_name,
                envvars=envvars,
                shell_cmd=shell_cmd,
            )
        )
        co(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "alpine",
                "sleep",
                "infinity",
            ]
        )

    else:
        runtime = DockerRuntime(
            DockerRuntimeConfig(
                compose_file=compose_file,
                service_name=service_name,
                envvars=envvars,
                shell_cmd=shell_cmd,
            )
        )

    # Connect before each test
    await runtime.connect()
    try:
        yield runtime
    finally:
        await runtime.disconnect()
        if runtime._from_compose:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                pass
        if runtime._from_container:
            try:
                co(["docker", "rm", "-f", container_name])
            except Exception:
                pass


@pytest.mark.serial
class TestDockerRuntimeCompose:
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connect and disconnect functionality."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
            """
            )
            compose_file = f.name

        try:
            runtime = DockerRuntime(DockerRuntimeConfig(compose_file=compose_file))

            # Test connect
            await runtime.connect()
            assert runtime.connected is True
            assert runtime.process is not None
            assert runtime.process.returncode is None

            # Test disconnect
            await runtime.disconnect()
            assert runtime.connected is False

            # Process should terminate after disconnect
            await asyncio.sleep(0.1)  # Give process time to terminate
            assert runtime.process.returncode is not None
        finally:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                raise

    @pytest.mark.asyncio
    async def test_from_compose(self):
        """Test creating runtime from compose file."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
            """
            )
            compose_file = f.name

        runtime = DockerRuntime(
            DockerRuntimeConfig(compose_file=compose_file, service_name="default")
        )

        assert f"docker compose -f {compose_file} exec default" in runtime.shell_cmd

        await runtime.disconnect()

    @pytest.mark.asyncio
    async def test_compose_service_not_exist(self):
        """Test when the compose service does not exist."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
            """
            )
            compose_file = f.name

        with pytest.raises(RuntimeError) as excinfo:
            async with docker_runtime(
                compose_file=compose_file, service_name="nonexistent-service"
            ):
                pass
        assert "Service nonexistent-service not found" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_run_simple_command(self):
        """Test running a simple echo command."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
            """
            )
            compose_file = f.name

        async with docker_runtime(
            compose_file=compose_file, shell_cmd="/bin/sh"
        ) as runtime:
            result = await runtime.run("echo 'Hello, World!'")
            assert "Hello, World!" in result

    @pytest.mark.asyncio
    async def test_run_multiple_commands(self):
        """Test running multiple commands in sequence."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
            """
            )
            compose_file = f.name

        async with docker_runtime(compose_file=compose_file) as runtime:
            result1 = await runtime.run("echo 'First Command'")
            assert "First Command" in result1

            result2 = await runtime.run("echo 'Second Command'")
            assert "Second Command" in result2

    @pytest.mark.asyncio
    async def test_run_with_env_vars(self):
        """Test running a command with environment variables."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
    environment:
        TEST_VAR1: ${TEST_VAR1}
        TEST_VAR2: ${TEST_VAR2}
            """
            )
            compose_file = f.name

        async with docker_runtime(
            compose_file=compose_file,
            envvars={
                "TEST_VAR1": "test_value1",
                "TEST_VAR2": "test_value2",
                "TEST_VAR3": "test_value3",
            },
        ) as runtime:
            result = await runtime.run("echo $TEST_VAR1")
            assert "test_value1" in result

            result = await runtime.run("echo $TEST_VAR2")
            assert "test_value2" in result

            result = await runtime.run("echo $TEST_VAR3")
            assert "test_value3" not in result

    @pytest.mark.asyncio
    async def test_runtime_info(self):
        """Test runtime_info method."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
            """
            )
            compose_file = f.name

        async with docker_runtime(compose_file=compose_file) as runtime:
            result = await runtime.runtime_info()
            assert "docker runtime" in result

    @pytest.mark.asyncio
    async def test_os_info(self):
        """Test os_info method."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
            """
            )
            compose_file = f.name

        async with docker_runtime(compose_file=compose_file) as runtime:
            result = await runtime.os_info()
            # For Alpine this should contain Alpine
            assert "Alpine" in result or "alpine" in result

    @pytest.mark.asyncio
    async def test_whoami(self):
        """Test whoami method."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
            """
            )
            compose_file = f.name

        async with docker_runtime(compose_file=compose_file) as runtime:
            result = await runtime.whoami()
            assert "root" in result

    @pytest.mark.asyncio
    async def test_has_systemd(self):
        """Test has_systemd method."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
            """
            )
            compose_file = f.name

        async with docker_runtime(compose_file=compose_file) as runtime:
            result = await runtime.has_systemd()
            assert "no systemd" in result

    @pytest.mark.asyncio
    async def test_discover_runtime(self):
        """Test that docker runtime can be discovered."""
        assert "docker" in Runtime.runtimes

        docker_runtime_class = Runtime.runtimes["docker"]
        assert issubclass(docker_runtime_class, Runtime)
        assert issubclass(docker_runtime_class, DockerRuntime)

    @pytest.mark.asyncio
    async def test_envvars_file_creation(self):
        """Test that the environment variables file is created and removed correctly."""
        with NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(
                """
services:
  default:
    image: alpine
    command: sleep infinity
            """
            )
            compose_file = f.name

        # Create runtime with env vars
        runtime = DockerRuntime(
            DockerRuntimeConfig(
                compose_file=compose_file,
                envvars={"TEST_ENV1": "value1", "TEST_ENV2": "value2"},
            )
        )

        # Verify the envvars_file was created
        assert os.path.exists(runtime.envvars_file)

        # Verify the content of the envvars_file
        with open(runtime.envvars_file, "r") as env_file:
            content = env_file.read()
            assert "TEST_ENV1=value1" in content
            assert "TEST_ENV2=value2" in content

        # Disconnect should remove the file
        await runtime.disconnect()
        assert not os.path.exists(runtime.envvars_file)


@pytest.mark.serial
class TestDockerRuntimeFromContainer:
    @pytest.mark.asyncio
    async def test_from_container(self):
        """Test that docker runtime can be created from a container."""
        async with docker_runtime(container_name="testbox") as runtime:
            assert runtime.connected is True
            assert runtime.from_container is True
            assert runtime.process is not None
            assert runtime.process.returncode is None

    @pytest.mark.asyncio
    async def test_container_name_not_exist(self):
        """Test when the container name does not exist."""
        runtime = DockerRuntime(
            DockerRuntimeConfig(container_name="nonexistent-container")
        )
        with pytest.raises(RuntimeError) as excinfo:
            await runtime.connect()
        assert "Failed to start docker container" in str(excinfo.value)
        assert (
            "Error response from daemon: No such container: nonexistent-container"
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    async def test_run_simple_command(self):
        """Test running a simple echo command."""
        async with docker_runtime(container_name="testbox") as runtime:
            result = await runtime.run("echo 'Hello, World!'")
            assert "Hello, World!" in result

    @pytest.mark.asyncio
    async def test_run_multiple_commands(self):
        """Test running multiple commands in sequence."""
        async with docker_runtime(container_name="testbox") as runtime:
            result1 = await runtime.run("echo 'First Command'")
            assert "First Command" in result1

            result2 = await runtime.run("echo 'Second Command'")
            assert "Second Command" in result2

    @pytest.mark.asyncio
    async def test_run_with_env_vars(self):
        """Test running a command with environment variables."""
        async with docker_runtime(
            container_name="testbox",
            envvars={"TEST_ENV1": "value1", "TEST_ENV2": "value2"},
        ) as runtime:
            result = await runtime.run("echo $TEST_ENV1")
            assert "value1" in result

            result = await runtime.run("echo $TEST_ENV2")
            assert "value2" in result

    @pytest.mark.asyncio
    async def test_runtime_info(self):
        """Test runtime_info method."""
        async with docker_runtime(container_name="testbox") as runtime:
            result = await runtime.runtime_info()
            assert "docker runtime" in result

    @pytest.mark.asyncio
    async def test_os_info(self):
        """Test os_info method."""
        async with docker_runtime(container_name="testbox") as runtime:
            result = await runtime.os_info()
            assert "Alpine" in result or "alpine" in result

    @pytest.mark.asyncio
    async def test_whoami(self):
        """Test whoami method."""
        async with docker_runtime(container_name="testbox") as runtime:
            result = await runtime.whoami()
            assert "root" in result

    @pytest.mark.asyncio
    async def test_has_systemd(self):
        """Test has_systemd method."""
        async with docker_runtime(container_name="testbox") as runtime:
            result = await runtime.has_systemd()
            assert "no systemd" in result
