"""Test that docs mention the pi export target."""

from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]


def test_exporting_md_mentions_pi_target():
    text = (_REPO_ROOT / "docs" / "EXPORTING.md").read_text()
    assert "### Pi target" in text
    assert "targets four deployment harnesses" in text


def test_readme_mentions_pi_target():
    text = (_REPO_ROOT / "README.md").read_text()
    assert "pi" in text.lower()
