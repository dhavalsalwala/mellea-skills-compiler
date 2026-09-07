"""Test that the export command's --help lists the pi target."""

from typer.testing import CliRunner

from mellea_skills_compiler.cli import app

runner = CliRunner()


def test_export_help_lists_pi_target():
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    normalized = " ".join(result.stdout.replace("│", " ").split())
    assert "claude-code | mcp | pi" in normalized
