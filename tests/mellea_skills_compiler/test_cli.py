"""Unit tests for CLI commands and argument validation.

Tests the typer-based CLI interface, focusing on argument parsing,
validation, and error handling without executing full compilation flows.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from mellea_skills_compiler.cli import app


runner = CliRunner()


class TestCompileBackendFlag:
    """Test the --backend flag validation and behavior."""

    @patch("mellea_skills_compiler.compile.mellea_skills.compile")
    def test_backend_claude_is_accepted(self, mock_compile):
        """Test that --backend claude is accepted and passed to compile function."""
        mock_compile.return_value = None

        result = runner.invoke(
            app,
            ["compile", "test_spec.md", "--backend", "claude"],
        )

        assert result.exit_code == 0
        mock_compile.assert_called_once()
        # Verify backend parameter was passed
        call_kwargs = mock_compile.call_args[1]
        assert call_kwargs["backend"] == "claude"

    @patch("mellea_skills_compiler.compile.mellea_skills.compile")
    def test_backend_invalid_is_accepted_by_cli(self, mock_compile):
        """Test that invalid backend is accepted by CLI (validation happens in compile)."""
        mock_compile.side_effect = ValueError("Unknown compilation backend")

        result = runner.invoke(
            app,
            ["compile", "test_spec.md", "--backend", "invalid"],
        )

        assert result.exit_code == 1
        # Error is logged but not captured in result output by typer
        # Just verify the exit code is correct

    @patch("mellea_skills_compiler.compile.mellea_skills.compile")
    def test_default_backend_is_claude(self, mock_compile):
        """Test that default backend is 'claude' when flag is omitted."""
        mock_compile.return_value = None

        result = runner.invoke(
            app,
            ["compile", "test_spec.md"],
        )

        assert result.exit_code == 0
        mock_compile.assert_called_once()
        # Verify default backend parameter
        call_kwargs = mock_compile.call_args[1]
        assert call_kwargs["backend"] == "claude"

    @patch("mellea_skills_compiler.compile.mellea_skills.compile")
    def test_backend_flag_short_form(self, mock_compile):
        """Test that -b short form of --backend flag works."""
        mock_compile.return_value = None

        result = runner.invoke(
            app,
            ["compile", "test_spec.md", "-b", "claude"],
        )

        assert result.exit_code == 0
        mock_compile.assert_called_once()
        call_kwargs = mock_compile.call_args[1]
        assert call_kwargs["backend"] == "claude"

    @patch("mellea_skills_compiler.compile.mellea_skills.compile")
    def test_multiple_backends_accepted_by_cli(self, mock_compile):
        """Test that any backend string is accepted by CLI (validation happens in compile)."""
        mock_compile.return_value = None

        result = runner.invoke(
            app,
            ["compile", "test_spec.md", "--backend", "bob"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_compile.call_args[1]
        assert call_kwargs["backend"] == "bob"

    @patch("mellea_skills_compiler.compile.mellea_skills.compile")
    def test_backend_parameter_passed_with_other_options(self, mock_compile):
        """Test that backend parameter works alongside other CLI options."""
        mock_compile.return_value = None

        result = runner.invoke(
            app,
            [
                "compile",
                "test_spec.md",
                "--backend",
                "claude",
                "--model",
                "claude-3-5-sonnet-20241022",
                "--timeout",
                "3600",
                "--repair-mode",
            ],
        )

        assert result.exit_code == 0
        mock_compile.assert_called_once()
        # Check positional and keyword arguments
        call_args = mock_compile.call_args
        # First positional arg is spec_path
        assert call_args[0][0] == Path("test_spec.md")
        # Second positional arg is model
        assert call_args[0][1] == "claude-3-5-sonnet-20241022"
        # Third positional arg is timeout
        assert call_args[0][2] == 3600
        # Check keyword arguments
        call_kwargs = call_args[1]
        assert call_kwargs["backend"] == "claude"
        assert call_kwargs["repair_mode"] is True


class TestCompileCommand:
    """Test the compile command basic functionality."""

    def test_compile_requires_spec_path(self):
        """Test that compile command requires spec_path argument."""
        result = runner.invoke(app, ["compile"])

        # Should fail due to missing required argument
        assert result.exit_code == 2  # Typer returns 2 for usage errors

    @patch("mellea_skills_compiler.compile.mellea_skills.compile")
    def test_compile_exception_handling(self, mock_compile):
        """Test that exceptions from compile function are handled gracefully."""
        mock_compile.side_effect = RuntimeError("Compilation failed")

        result = runner.invoke(
            app,
            ["compile", "test_spec.md"],
        )

        assert result.exit_code == 1
        # Error is logged but not captured in stdout by typer
        # Just verify the exit code and that compile was called
        mock_compile.assert_called_once()


class TestOtherCommands:
    """Smoke tests for other CLI commands to ensure they're not broken."""

    def test_validate_command_exists(self):
        """Test that validate command is available."""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout.lower()

    def test_run_command_exists(self):
        """Test that run command is available."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "run" in result.stdout.lower()

    def test_ingest_command_exists(self):
        """Test that ingest command is available."""
        result = runner.invoke(app, ["ingest", "--help"])
        assert result.exit_code == 0
        assert "ingest" in result.stdout.lower()

    def test_certify_command_exists(self):
        """Test that certify command is available."""
        result = runner.invoke(app, ["certify", "--help"])
        assert result.exit_code == 0
        assert "certify" in result.stdout.lower()

    def test_export_command_exists(self):
        """Test that export command is available."""
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0
        assert "export" in result.stdout.lower()
