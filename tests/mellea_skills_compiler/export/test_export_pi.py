import json
from pathlib import Path

import pytest

from mellea_skills_compiler.export.exporter import Invocation, run_export

_WEATHER_SKILL = Path(__file__).parents[3] / "examples/weather/weather_mellea"


def test_pi_target_accepted(tmp_path):
    out_path = tmp_path / "weather_mellea-pi"
    inv = Invocation(
        package_path=_WEATHER_SKILL, target="pi", out_path=out_path, force=True
    )
    result = run_export(inv)
    assert result.out_path == out_path


def test_pi_target_emits_skill_md_and_run_sh(tmp_path):
    out_path = tmp_path / "weather_mellea-pi"
    inv = Invocation(
        package_path=_WEATHER_SKILL, target="pi", out_path=out_path, force=True
    )
    run_export(inv)
    assert (out_path / "SKILL.md").exists()
    assert (out_path / "scripts" / "run.sh").exists()


def test_pi_target_next_steps_reference_pi_skills_dir(tmp_path):
    out_path = tmp_path / "weather_mellea-pi"
    inv = Invocation(
        package_path=_WEATHER_SKILL, target="pi", out_path=out_path, force=True
    )
    run_export(inv)
    notes = (out_path / "EXPORT_NOTES.md").read_text()
    assert ".pi/skills/" in notes or ".agents/skills/" in notes
