from mellea_skills_compiler.export.exporter import ParsedSignature
from mellea_skills_compiler.export.targets.langgraph import _render_readme


def test_readme_synchronous_oneshot_invocation_uses_real_state_key():
    """graph.py's synchronous_oneshot node reads state.<param_name> (see
    _named_async_call), not state["input"] — the README's example must use
    the same key or following it produces an empty/default field value."""
    sig = ParsedSignature(
        function_name="run_pipeline",
        params=[{"name": "query", "type": "str", "required": True, "default": None}],
        return_type="str",
        pattern="single_positional",
    )
    result = _render_readme(
        graph_name="weather-mellea",
        sig=sig,
        env_vars=[],
        modality="synchronous_oneshot",
    )
    assert '"query":' in result
    assert '"input":' not in result
