import pytest

from opsmate.tools.command_line import ShellCommand
from opsmate.tests.base import BaseTestCase


class TestCommandLine(BaseTestCase):
    @pytest.mark.asyncio
    async def test_command_line(self):
        tool = ShellCommand(
            command="ls -l",
            description="List the contents of the current directory",
        )
        assert tool.output is None

        result = await tool.run()
        assert result is not None
        assert result == tool.output

        assert tool.markdown() is not None
        assert tool.output in tool.markdown()

    @pytest.mark.asyncio
    async def test_command_line_with_context(self):
        tool = ShellCommand(
            command="echo $TEST",
            description="List the contents of the current directory",
        )
        result = await tool.run(context={"envvars": {"TEST": "test"}})
        assert result is not None
        assert result == "test\n"

        result = await tool.run(context={"envvars": {"TEST": "test2"}})
        assert result is not None
        assert result == "test2\n"
