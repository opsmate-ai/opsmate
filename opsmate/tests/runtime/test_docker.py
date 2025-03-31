import pytest
import asyncio
from opsmate.runtime import DockerRuntime, RuntimeError, Runtime
from opsmate.runtime.docker import DockerRuntimeConfig
from contextlib import asynccontextmanager
import os
from tempfile import NamedTemporaryFile
import uuid
import subprocess


@asynccontextmanager
async def docker_runtime(
    compose_file="docker-compose.yml",
    service_name="default",
    container_name="",
    shell_cmd="/bin/sh",
    envvars={},
):
    runtime = DockerRuntime(
        DockerRuntimeConfig(
            compose_file=compose_file,
            service_name=service_name,
            container_name=container_name,
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


@pytest.mark.serial
@pytest.mark.skipif(
    os.getenv("DOCKER_RUNTIME_TESTS") != "true",
    reason="DOCKER_RUNTIME_TESTS is not set",
)
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

        try:
            runtime = DockerRuntime(
                DockerRuntimeConfig(compose_file=compose_file, service_name="default")
            )

            assert f"docker compose -f {compose_file} exec default" in runtime.shell_cmd

            await runtime.disconnect()
        finally:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_container_name_handling(self):
        """Test that providing container_name without _from_container implementation raises an error."""
        # This test verifies the behavior when container_name is provided
        # but the _from_container method is not implemented/commented out
        with pytest.raises(AttributeError) as excinfo:
            DockerRuntime(DockerRuntimeConfig(container_name="nonexistent-container"))

        # Verify the error is related to _from_container method
        assert "_from_container" in str(excinfo.value)

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

        try:
            async with docker_runtime(
                compose_file=compose_file, shell_cmd="/bin/sh"
            ) as runtime:
                result = await runtime.run("echo 'Hello, World!'")
                assert "Hello, World!" in result
        finally:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                pass

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

        try:
            async with docker_runtime(compose_file=compose_file) as runtime:
                result1 = await runtime.run("echo 'First Command'")
                assert "First Command" in result1

                result2 = await runtime.run("echo 'Second Command'")
                assert "Second Command" in result2
        finally:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                pass

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

        try:
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
        finally:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                pass

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

        try:
            async with docker_runtime(compose_file=compose_file) as runtime:
                result = await runtime.runtime_info()
                assert "docker runtime" in result
        finally:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                pass

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

        try:
            async with docker_runtime(compose_file=compose_file) as runtime:
                result = await runtime.os_info()
                # For Alpine this should contain Alpine
                assert "Alpine" in result or "alpine" in result
        finally:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                pass

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

        try:
            async with docker_runtime(compose_file=compose_file) as runtime:
                result = await runtime.whoami()
                assert "root" in result
        finally:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                pass

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

        try:
            async with docker_runtime(compose_file=compose_file) as runtime:
                result = await runtime.has_systemd()
                assert "no systemd" in result
        finally:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                pass

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

        try:
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

        finally:
            try:
                subprocess.run(
                    f"docker compose -f {compose_file} down", shell=True, check=False
                )
                os.remove(compose_file)
            except Exception:
                pass
