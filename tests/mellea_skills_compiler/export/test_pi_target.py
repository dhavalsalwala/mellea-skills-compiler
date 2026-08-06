import re

from mellea_skills_compiler.export.targets.pi import _to_pi_name

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
