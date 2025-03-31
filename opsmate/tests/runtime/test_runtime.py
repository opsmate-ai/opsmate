import pytest
import asyncio
from opsmate.runtime import LocalRuntime, RuntimeError, Runtime
from opsmate.runtime.local import LocalRuntimeConfig
from contextlib import asynccontextmanager


@asynccontextmanager
async def local_runtime(envvars={}):
    runtime = LocalRuntime(LocalRuntimeConfig(envvars=envvars))
    # Connect before each test
    await runtime.connect()
    try:
        yield runtime
    finally:
        await runtime.disconnect()


class TestLocalRuntime:
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connect and disconnect functionality."""
        runtime = LocalRuntime()

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

    @pytest.mark.asyncio
    async def test_run_simple_command(self):
        """Test running a simple echo command."""

        async with local_runtime() as runtime:
            result = await runtime.run("echo 'Hello, World!'")
            assert "Hello, World!" in result

    @pytest.mark.asyncio
    async def test_run_multiple_commands(self):
        """Test running multiple commands in sequence."""

        async with local_runtime() as runtime:
            result1 = await runtime.run("echo 'First Command'")
            assert "First Command" in result1

            result2 = await runtime.run("echo 'Second Command'")
            assert "Second Command" in result2

    @pytest.mark.asyncio
    async def test_run_with_env_vars(self):
        """Test running a command with environment variables."""
        async with local_runtime(envvars={"TEST_VAR": "test_value"}) as runtime:
            result = await runtime.run("echo $TEST_VAR")
            assert "test_value" in result

    @pytest.mark.asyncio
    async def test_run_command_with_output(self):
        """Test running a command that produces multiple lines of output."""
        async with local_runtime() as runtime:
            result = await runtime.run(
                "echo 'Line 1' && echo 'Line 2' && echo 'Line 3'"
            )
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    @pytest.mark.asyncio
    async def test_run_timeout(self):
        """Test that a command timeout raises an error."""
        async with local_runtime() as runtime:
            # Run a sleep command that should timeout
            with pytest.raises(RuntimeError):
                # Set a short timeout of 0.5 seconds but run sleep for 10 seconds
                await runtime.run("sleep 10", timeout=0.5)

    @pytest.mark.asyncio
    async def test_run_auto_connect(self):
        """Test that run automatically connects if not connected."""
        runtime = LocalRuntime()
        # Don't explicitly connect

        try:
            # Run should automatically connect
            result = await runtime.run("echo 'Auto Connect Test'")
            assert "Auto Connect Test" in result
            assert runtime.connected is True
        finally:
            # Clean up
            await runtime.disconnect()

    @pytest.mark.asyncio
    async def test_run_after_disconnect(self):
        """Test that run reconnects after disconnect."""
        # First run a command
        async with local_runtime() as runtime:
            result1 = await runtime.run("echo 'Before Disconnect'")
            assert "Before Disconnect" in result1

        # Disconnect
        await runtime.disconnect()
        assert runtime.connected is False

        # Run should automatically reconnect
        try:
            result2 = await runtime.run("echo 'After Reconnect'")
            assert "After Reconnect" in result2
            assert runtime.connected is True
        finally:
            await runtime.disconnect()

    @pytest.mark.asyncio
    async def test_working_directory(self):
        """Test command execution preserves working directory."""
        # Get current directory
        async with local_runtime() as runtime:
            result1 = await runtime.run("pwd")

            # Change to /tmp
            await runtime.run("cd /tmp")

            # Verify we're in /tmp
            result2 = await runtime.run("pwd")

            assert result2.strip() == "/tmp"

    @pytest.mark.asyncio
    async def test_discover_runtimes(self):
        """Test that runtimes can be discovered."""
        # runtimes = discover_runtimes()
        assert "local" in Runtime.runtimes

        local_runtime = Runtime.runtimes["local"]
        assert issubclass(local_runtime, Runtime)
        assert issubclass(local_runtime, LocalRuntime)
