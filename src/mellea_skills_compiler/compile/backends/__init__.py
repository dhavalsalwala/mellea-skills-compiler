"""Backend implementations for mellea-skills compilation.

This package contains concrete implementations of the CompilationBackend protocol,
each wrapping a different compilation engine (Claude Code, IBM Bob, local LLMs, etc.).

Available backends:
- claude_code: Uses Anthropic's Claude Code CLI for compilation
"""

from mellea_skills_compiler.compile.backend import global_registry
from mellea_skills_compiler.compile.backends.bob import BOBBackend
from mellea_skills_compiler.compile.backends.claude_code import ClaudeCodeBackend
from mellea_skills_compiler.enums import BackendCompiler


# Register the Claude Code backend
global_registry.register_backend(
    identifier=BackendCompiler.CLAUDE_CODE, backend_class=ClaudeCodeBackend
)
global_registry.register_backend(
    identifier=BackendCompiler.IBM_BOB, backend_class=BOBBackend
)

__all__ = ["ClaudeCodeBackend", "BOBBackend"]
