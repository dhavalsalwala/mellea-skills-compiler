from pathlib import Path

from mellea_skills_compiler.export.exporter import (
    AdapterFile,
    Invocation,
    LoadedContext,
    ParsedSignature,
    TranslationPlan,
    _build_export_notes,
)


def test_export_notes_langgraph_invocation_uses_real_state_key(tmp_path):
    """EXPORT_NOTES.md's langgraph next-step must invoke graph.ainvoke with the
    real state field (e.g. "query"), not the placeholder "input" — the
    generated graph.py node reads state.<param_name>, so following the
    "input" example leaves the real field at its empty default."""
    sig = ParsedSignature(
        function_name="run_pipeline",
        params=[{"name": "query", "type": "str", "required": True, "default": None}],
        return_type="str",
        pattern="single_positional",
    )
    loaded = LoadedContext(
        invocation=Invocation(
            package_path=tmp_path, target="langgraph", out_path=tmp_path / "out"
        ),
        manifest={"package_name": "weather_mellea", "modality": "synchronous_oneshot"},
        package_source_dir=tmp_path,
        python_package_dir=tmp_path,
        supporting_asset_dirs=[],
        entry_module="pipeline",
        sig=sig,
        policy_manifest_path=None,
    )
    plan = TranslationPlan(
        graph_name="weather_mellea",
        adapter_files=[AdapterFile("graph.py", "")],
        bundled_package_name="weather_mellea",
    )

    notes = _build_export_notes(plan, loaded)

    assert "'query':" in notes
    assert "'input':" not in notes
