"""Pi target: translate a LoadedContext into a TranslationPlan.

Supported modalities:
  synchronous_oneshot   — sync Python subprocess via scripts/run.sh
  streaming             — unbuffered async streaming via scripts/run.sh
  conversational_session — session carry-forward via --session JSON arg
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from mellea_skills_compiler.export.exporter import (
        AdapterFile,
        LoadedContext,
        ParsedSignature,
        TranslationPlan,
    )

SUPPORTED_MODALITIES = {
    "synchronous_oneshot",
    "streaming",
    "conversational_session",
}


def _to_pi_name(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    s = s[:64].strip("-")
    return s or "pipeline"
