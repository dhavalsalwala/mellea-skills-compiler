import re

import yaml

from mellea_skills_compiler.export.targets.pi import _to_pi_name, _render_skill_md

PI_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def test_to_pi_name_lowercases_and_hyphenates():
    assert _to_pi_name("Weather_Mellea") == "weather-mellea"


def test_to_pi_name_strips_leading_trailing_hyphens():
    assert _to_pi_name("__weather__") == "weather"


def test_to_pi_name_collapses_consecutive_hyphens():
    assert _to_pi_name("weather___mellea") == "weather-mellea"


def test_to_pi_name_empty_falls_back_to_pipeline():
    assert _to_pi_name("___") == "pipeline"


def test_to_pi_name_matches_pi_regex():
    for raw in ["My Weather Skill", "weather_mellea", "a1_b2-c3", ""]:
        assert PI_NAME_RE.match(_to_pi_name(raw))


def test_to_pi_name_respects_64_char_limit():
    long_name = "a" * 100
    assert len(_to_pi_name(long_name)) <= 64


from mellea_skills_compiler.export.exporter import LoadedContext, ParsedSignature


def _minimal_loaded_context(tmp_path, *, modality="synchronous_oneshot"):
    from mellea_skills_compiler.export.exporter import Invocation

    pkg_dir = tmp_path / "weather_mellea"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")

    inv = Invocation(package_path=tmp_path, target="pi", out_path=tmp_path / "out")
    manifest = {
        "package_name": "weather_mellea",
        "modality": modality,
        "entry_signature": "run_pipeline() -> str",
    }
    sig = ParsedSignature(
        function_name="run_pipeline", params=[], return_type="str", pattern="no_args"
    )
    return LoadedContext(
        invocation=inv,
        manifest=manifest,
        package_source_dir=tmp_path,
        python_package_dir=pkg_dir,
        supporting_asset_dirs=[],
        entry_module="pipeline",
        sig=sig,
        policy_manifest_path=None,
    )


def test_translate_pi_produces_four_adapter_files(tmp_path):
    from mellea_skills_compiler.export.targets.pi import translate_pi

    loaded = _minimal_loaded_context(tmp_path)
    plan = translate_pi(loaded)

    paths = {af.relative_path for af in plan.adapter_files}
    assert paths == {"SKILL.md", "scripts/run.sh", "pyproject.toml", "README.md"}
    assert plan.graph_name == "weather-mellea"
    assert plan.bundled_package_name == "weather_mellea"


def test_translate_pi_unsupported_modality_falls_back(tmp_path):
    from mellea_skills_compiler.export.targets.pi import translate_pi

    loaded = _minimal_loaded_context(tmp_path, modality="scheduled")
    plan = translate_pi(loaded)

    assert any("Falling back to synchronous_oneshot" in w for w in plan.warnings)


def _frontmatter(skill_md: str) -> dict:
    _, fm_block, _ = skill_md.split("---", 2)
    return yaml.safe_load(fm_block)


def test_skill_md_frontmatter_has_required_fields():
    result = _render_skill_md(
        manifest={"package_name": "weather_mellea"},
        skill_name="weather-mellea",
        modality="synchronous_oneshot",
        sig=ParsedSignature(
            function_name="run_pipeline", params=[], return_type="str", pattern="no_args"
        ),
    )
    fm = _frontmatter(result)
    assert fm["name"] == "weather-mellea"
    assert fm["description"] == "A Mellea pipeline skill."
    assert "compatibility" in fm


def test_skill_md_frontmatter_omits_unused_fields():
    result = _render_skill_md(
        manifest={"package_name": "weather_mellea"},
        skill_name="weather-mellea",
        modality="synchronous_oneshot",
        sig=ParsedSignature(
            function_name="run_pipeline", params=[], return_type="str", pattern="no_args"
        ),
    )
    fm = _frontmatter(result)
    for unused in ("license", "metadata", "allowed-tools", "disable-model-invocation"):
        assert unused not in fm


def test_skill_md_name_matches_pi_regex():
    result = _render_skill_md(
        manifest={"package_name": "Weather_Mellea"},
        skill_name=_to_pi_name("Weather_Mellea"),
        modality="synchronous_oneshot",
        sig=ParsedSignature(
            function_name="run_pipeline", params=[], return_type="str", pattern="no_args"
        ),
    )
    fm = _frontmatter(result)
    assert PI_NAME_RE.match(fm["name"])
