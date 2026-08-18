def test_invocation_args_single_positional_includes_trailing_optional_params():
    """run_pipeline(input_text: str, check_mode: str = "validate") is classified
    single_positional (exactly one required param), but has two params total.
    _invocation_args must pass both through as positional argv, not silently
    drop the optional one — same underlying bug reported against the pi
    target in PR #57 review, inherited verbatim from this module."""
    from mellea_skills_compiler.export.targets.claude_code import _invocation_args

    params = [
        {"name": "input_text", "type": "str", "required": True, "default": None},
        {"name": "check_mode", "type": "str", "required": False, "default": '"validate"'},
    ]
    result = _invocation_args("single_positional", params)
    assert result == "sys.argv[2], sys.argv[3]"


def test_invocation_args_single_positional_with_no_optional_params_unchanged():
    from mellea_skills_compiler.export.targets.claude_code import _invocation_args

    params = [{"name": "query", "type": "str", "required": True, "default": None}]
    result = _invocation_args("single_positional", params)
    assert result == "sys.argv[2]"
