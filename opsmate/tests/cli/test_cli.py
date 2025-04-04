import pytest
import sys
from click.testing import CliRunner
from io import StringIO
from opsmate.cli.cli import opsmate_cli
import os


@pytest.fixture
def cli_runner():
    # Store original environment variables
    original_endpoint = os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    original_headers = os.environ.pop("OTEL_EXPORTER_OTLP_HEADERS", None)

    yield CliRunner()

    # Restore original environment variables if they existed
    if original_endpoint is not None:
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = original_endpoint
    if original_headers is not None:
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = original_headers


@pytest.fixture
def capture_stdout():
    """Capture stdout for testing console output"""
    original_stdout = sys.stdout
    sys.stdout = StringIO()
    yield sys.stdout
    sys.stdout = original_stdout


class TestRunCommandIntegration:
    def test_run_help(self, cli_runner):
        """Test that the run command shows help correctly"""
        result = cli_runner.invoke(opsmate_cli, ["run", "--help"])

        assert result.exit_code == 0
        assert "Run a task with the Opsmate" in result.output
        assert "--model" in result.output
        assert "--context" in result.output
        assert "-nt" in result.output
        assert "--no-tool-output" in result.output
        assert "-no" in result.output
        assert "--no-observation" in result.output

    def test_run_basic(self, cli_runner):
        """Test that the run command works with a basic instruction"""
        result = cli_runner.invoke(opsmate_cli, ["run", "print 'hello world'"])

        assert result.exit_code == 0
        # assert "hello world" in result.output

    def test_run_with_different_model(self, cli_runner):
        """Test that the run command works with a different model"""
        result = cli_runner.invoke(
            opsmate_cli,
            [
                "run",
                "print 'hello world'",
                "--model",
                "claude-3-5-sonnet-20241022",
                "--tools",
                "ShellCommand",
                "--loglevel",
                "ERROR",
            ],
        )
        assert result.exit_code == 0
        # assert "hello world" in result.output.lower()

    def test_run_with_system_prompt(self, cli_runner):
        """Test that the run command works with a system prompt"""
        result = cli_runner.invoke(
            opsmate_cli,
            [
                "run",
                "print hello",
                "--system-prompt",
                "You print hola only, replace hello with hola",
                "--tools",
                "ShellCommand",
                "--loglevel",
                "ERROR",
            ],
        )

        assert result.exit_code == 0
        # assert "hola" in result.output.lower()

    def test_run_with_invalid_model(self, cli_runner):
        """Test that the run command works with a invalid model"""
        result = cli_runner.invoke(
            opsmate_cli, ["run", "print 'hello world'", "--model", "invalid_model"]
        )
        assert result.exit_code == 1
        # assert "Error: No provider found for model: invalid_model" in result.output

    def test_run_with_invalid_tool(self, cli_runner):
        """Test that the run command works with a invalid tool"""
        result = cli_runner.invoke(
            opsmate_cli, ["run", "print 'hello world'", "--tools", "invalid_tool"]
        )
        assert result.exit_code == 1
        assert "Error: Tool invalid_tool not found." in result.output

    def test_run_with_no_tool_output(self, cli_runner):
        """Test that the run command works with no tool output"""
        result = cli_runner.invoke(
            opsmate_cli,
            [
                "run",
                "print hello world case",
                "-nt",
                "--tools",
                "ShellCommand",
                "--loglevel",
                "ERROR",
            ],
        )
        assert result.exit_code == 0
        # assert "hello world" in result.output.lower()
        # assert "### Tool outputs" not in result.output

    def test_run_with_no_observation(self, cli_runner):
        """Test that the run command works with no observation"""
        result = cli_runner.invoke(
            opsmate_cli,
            [
                "run",
                "print 'hello world'",
                "-no",
                "--tools",
                "ShellCommand",
                "--loglevel",
                "ERROR",
            ],
        )
        assert result.exit_code == 0
        # assert "hello world" in result.output.lower()
        # assert "### Tool outputs" in result.output
        # assert "### Observation" not in result.output


class TestSolveCommandIntegration:
    def test_solve_help(self, cli_runner):
        """Test that the solve command shows help correctly"""
        result = cli_runner.invoke(opsmate_cli, ["solve", "--help"])

        assert result.exit_code == 0
        assert "Solve a problem with the Opsmate" in result.output
        assert "--model" in result.output
        assert "--context" in result.output
        assert "-i" in result.output
        assert "--max-iter" in result.output
        assert "--no-tool-output" in result.output
        assert "--tool-calls-per-action" in result.output

    def test_solve_basic(self, cli_runner):
        """Test that the solve command works with a basic instruction"""
        result = cli_runner.invoke(opsmate_cli, ["solve", "print 'hello world'"])

        assert result.exit_code == 0
        assert "Answer" in result.output

    def test_solve_with_max_iter(self, cli_runner):
        """Test that the solve command works with a max iter"""
        result = cli_runner.invoke(
            opsmate_cli, ["solve", "print 'hello world'", "--max-iter", "10"]
        )

        assert result.exit_code == 0
        assert "Answer" in result.output

    def test_solve_with_invalid_tools(self, cli_runner):
        """Test that the solve command works with invalid tools"""
        result = cli_runner.invoke(
            opsmate_cli, ["solve", "print 'hello world'", "--tools", "invalid-tool"]
        )

        assert result.exit_code == 1
        assert "Error: Tool invalid-tool not found." in result.output

    def test_solve_with_selected_tool(self, cli_runner):
        """Test that the solve command works with a selected tool"""
        result = cli_runner.invoke(
            opsmate_cli, ["solve", "print 'hello world'", "--tools", "ShellCommand"]
        )

        assert result.exit_code == 0

    def test_solve_with_tool_from_discovery(self, cli_runner):
        """Test that the solve command works with a tool from discovery"""
        result = cli_runner.invoke(
            opsmate_cli,
            ["solve", "what's the current time?", "--tools", "current_time"],
        )

        assert result.exit_code == 0

    def test_solve_with_answer_only(self, cli_runner):
        """Test that the solve command works with an answer only"""
        result = cli_runner.invoke(
            opsmate_cli, ["solve", "what's the current time?", "--answer-only"]
        )

        assert result.exit_code == 0

    def test_solve_with_no_tool_output(self, cli_runner):
        """Test that the solve command works with no tool output"""
        result = cli_runner.invoke(
            opsmate_cli, ["solve", "what's the current time?", "-nt"]
        )

        assert result.exit_code == 0
