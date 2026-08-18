"""Backend implementations for mellea-skills compilation.

This package contains concrete implementations of the CompilationBackend protocol,
each wrapping a different compilation engine (Claude Code, IBM Bob, local LLMs, etc.).

Available backends:
- claude: Uses Anthropic's Claude Code CLI for compilation
- bob: Uses IBM Bob CLI for compilation
"""

from mellea_skills_compiler.compile.backend import global_registry
from mellea_skills_compiler.compile.backends.bob import BOBBackend
from mellea_skills_compiler.compile.backends.claude import ClaudeCodeBackend


# Register the Claude Code backend
global_registry.register_backend(backend_class=ClaudeCodeBackend)

# Register the IBM Bob backend
global_registry.register_backend(backend_class=BOBBackend)

__all__ = ["ClaudeCodeBackend", "BOBBackend"]
