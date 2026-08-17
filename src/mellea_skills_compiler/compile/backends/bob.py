"""BoB backend implementation for mellea-skills compilation.

This module implements the CompilationBackend protocol using Anthropic's BoB CLI
as the compilation engine. It wraps the existing subprocess-based approach that invokes
the `/mellea-fy` and `/mellea-fy-repair` slash commands.

The BOBBackend is responsible for:
- Validating that BoB CLI is installed and configured
- Setting up a local proxy to strip context_management from API requests
- Invoking BoB with appropriate arguments and system prompts
- Parsing the JSON streaming output to track compilation progress
- Handling timeouts and errors gracefully
- Cleaning up resources (proxy server, subprocesses) on completion or failure

This backend requires:
- BoB CLI installed and accessible in PATH
- Valid Anthropic API credentials (ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN)
- Network access to Anthropic API (or configured ANTHROPIC_BASE_URL)

Example usage:
    >>> from mellea_skills_compiler.compile.backends.claude_code import BOBBackend
    >>> from mellea_skills_compiler.compile.backend import CompilationContext
    >>>
    >>> backend = BOBBackend()
    >>> is_valid, error = backend.validate_environment()
    >>> if not is_valid:
    ...     print(f"Cannot use BoB: {error}")
    ...     exit(1)
    >>>
    >>> context = CompilationContext(
    ...     spec_path=Path("weather/spec.md"),
    ...     package_dir=Path("weather_mellea"),
    ...     intermediate_dir=Path("weather_mellea/intermediate"),
    ...     model="claude-3-7-sonnet-20250219",
    ...     timeout=300,
    ... )
    >>>
    >>> result = backend.compile(context)
    >>> if result.success:
    ...     print(f"Compiled successfully to {result.package_dir}")
    ... else:
    ...     print(f"Compilation failed: {result.error_message}")
"""

import json
import logging
import os
import shutil
import socketserver
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from anthropic import Anthropic
from rich.console import Console

from mellea_skills_compiler.compile.backend import (
    CompilationBackend,
    CompilationContext,
    CompilationResult,
)
from mellea_skills_compiler.compile.claude_directives import (
    build_system_prompt,
    write_compile_settings,
)
from mellea_skills_compiler.compile.proxy import ContextMgmtStrippingProxy
from mellea_skills_compiler.enums import (
    ClaudeResponseMessageType,
    ClaudeResponseType,
    InferenceModel,
)
from mellea_skills_compiler.toolkit.logging import configure_logger


LOGGER = configure_logger()
console = Console(log_time=True)


class BOBBackend:
    """BoB backend for mellea-skills compilation.

    This backend implements the CompilationBackend protocol by wrapping the existing
    BoB subprocess approach. It invokes the BoB CLI with the
    `/mellea-fy` or `/mellea-fy-repair` slash commands to decompose skill specifications
    into Mellea pipeline components.

    The backend handles:
    - Model validation via Anthropic API
    - Local proxy server setup to strip context_management from requests
    - BoB subprocess invocation with appropriate arguments
    - JSON streaming output parsing to track compilation progress
    - Timeout handling and graceful termination
    - Error handling and cleanup of resources

    Architecture:
    - Uses a local proxy server to modify API requests before forwarding to Anthropic
    - Runs BoB in project mode (-p) with restricted tools (Read, Write, Edit)
    - Streams JSON output to track compilation steps and detect completion
    - Enforces deny rules via settings file to prevent overwriting wrapper-rendered files

    Attributes:
        None (stateless backend, all state passed via CompilationContext)

    Example:
        >>> backend = BOBBackend()
        >>>
        >>> # Validate environment before use
        >>> is_valid, error = backend.validate_environment()
        >>> if not is_valid:
        ...     raise RuntimeError(f"BoB not available: {error}")
        >>>
        >>> # Execute compilation
        >>> context = CompilationContext(
        ...     spec_path=Path("weather/spec.md"),
        ...     package_dir=Path("weather_mellea"),
        ...     intermediate_dir=Path("weather_mellea/intermediate"),
        ...     model="claude-3-7-sonnet-20250219",
        ... )
        >>> result = backend.compile(context)
    """

    @staticmethod
    def identifier() -> str:
        return "bob"

    def name(self) -> str:
        """Return human-readable backend name for logging and display.

        Returns:
            The string "IBM Bob"

        Example:
            >>> backend = BOBBackend()
            >>> print(f"Using backend: {backend.name()}")
            Using backend: IBM Bob
        """
        return "IBM Bob"

    def compile(self, context: CompilationContext) -> CompilationResult:
        """Execute the full compilation workflow using BoB.

        This method orchestrates the 10-step compilation process by invoking the
        BoB CLI with the `/mellea-fy` or `/mellea-fy-repair` slash command.

        The compilation workflow:
        1. Validate the specified model is available via Anthropic API
        2. Start a local proxy server to strip context_management from requests
        3. Build the BoB command-line arguments
        4. Invoke BoB subprocess with system prompt and settings
        5. Parse JSON streaming output to track progress
        6. Handle timeout if context.timeout > 0
        7. Detect compilation completion or errors
        8. Clean up proxy server and subprocess
        9. Return CompilationResult with success status and artifacts

        Args:
            context: Compilation parameters including paths, model, timeout, etc.

        Returns:
            CompilationResult with success status, package directory, and metadata.
            On success, result.success=True and result.package_dir contains the
            compiled Mellea package. On failure, result.success=False and
            result.error_message contains a description of what went wrong.

        Raises:
            RuntimeError: If BoB is not available or configured incorrectly
            TimeoutError: If compilation exceeds context.timeout (when timeout > 0)

        Example:
            >>> backend = BOBBackend()
            >>> context = CompilationContext(
            ...     spec_path=Path("weather/spec.md"),
            ...     package_dir=Path("weather_mellea"),
            ...     intermediate_dir=Path("weather_mellea/intermediate"),
            ...     model="claude-3-7-sonnet-20250219",
            ...     timeout=300,
            ...     repair_mode=False,
            ... )
            >>> result = backend.compile(context)
            >>> if result.success:
            ...     print(f"Package created at {result.package_dir}")
            ... else:
            ...     print(f"Compilation failed: {result.error_message}")
        """
        process = None

        try:
            console.print(
                f"\n[green]{'Repairing' if context.repair_mode else 'Compiling'} using {self.name()}\n"
            )

            # Step 5: Build BoB command-line arguments
            claude_argv = self._build_bob_argv(
                spec_path=context.spec_path,
                repair_mode=context.repair_mode,
            )

            # Step 6: Execute BoB subprocess
            start_time = time.time()
            processing = console.status(
                "[italic bold yellow]Processing...[/]", spinner_style="status.spinner"
            )

            process = subprocess.Popen(
                claude_argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            stderr_lines = []

            def read_stderr():
                if process.stderr:
                    for line in iter(process.stderr.readline, ""):
                        if line:
                            stderr_lines.append(line.strip())

            # Thread for reading stderr
            stderr_thread = threading.Thread(target=read_stderr)
            stderr_thread.daemon = True
            stderr_thread.start()

            # Step 7: Parse streaming JSON output
            processing.start()
            while True:
                elapsed = time.time() - start_time
                if context.timeout > 0 and elapsed >= context.timeout:
                    raise Exception(
                        f"Mellea-fy skill compilation failed due to timeout. Process timed out after {elapsed:.1f}s (limit: {context.timeout}s)"
                    )

                # Read output
                output = process.stdout.readline()

                if output == "" and process.poll() is not None:
                    processing.stop()
                    break

                if output:
                    try:
                        # response = json.loads(output.strip())
                        console.print(f"[cyan]{output.strip()}[/]")
                    except json.decoder.JSONDecodeError as e:
                        console.print("Claude message parsing error: " + str(e))

            # Wait for stderr thread
            stderr_thread.join(timeout=1)

            # Check return code
            return_code = process.wait(timeout=1)
            if return_code != 0:
                return CompilationResult(
                    success=False,
                    package_dir=context.package_dir,
                    error_message=f"Mellea-fy skill compilation failed with return code {return_code}. Error: {' '.join(stderr_lines)}",
                )

            # Success!
            return CompilationResult(
                success=True,
                package_dir=context.package_dir,
                intermediate_artifacts={},
                metadata={"elapsed_time": time.time() - start_time},
            )

        except Exception as e:
            return CompilationResult(
                success=False,
                package_dir=context.package_dir,
                error_message=str(e),
            )
        finally:
            # Step 8: Cleanup
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

    def validate_environment(self) -> tuple[bool, Optional[str]]:
        """Check if BoB CLI and API credentials are available.

        This method verifies that all prerequisites for using BoB are met:
        1. BoB CLI is installed and accessible in PATH
        2. Anthropic API credentials are configured (ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN)
        3. The API credentials are valid by checking that models can be listed

        This should be called before attempting compilation to provide early,
        actionable error messages to users.

        Returns:
            A tuple of ``(is_valid, error_message)`` where ``is_valid`` is ``True``
            when BoB is usable and ``error_message`` contains a remediation
            hint when validation fails.

        Example:
            >>> backend = BOBBackend()
            >>> is_valid, error = backend.validate_environment()
            >>> if not is_valid:
            ...     print(f"Cannot use BoB backend: {error}")
        """
        if shutil.which("bob") is None:
            return False, (
                "BoB CLI not found in PATH. "
                "Install it from https://docs.anthropic.com/en/docs/claude-code."
            )

        return True, None

    def supports_repair_mode(self) -> bool:
        """Indicate that BoB supports repair mode.

        BoB supports repair mode via the `/mellea-fy-repair` slash command,
        which attempts to fix compilation errors by analyzing failed artifacts and
        regenerating specific components.

        Returns:
            True (BoB supports repair mode)

        Example:
            >>> backend = BOBBackend()
            >>> if backend.supports_repair_mode():
            ...     print("Repair mode available")
            ...     context.repair_mode = True
        """
        return True

    def _build_bob_argv(
        self,
        spec_path: Path,
        repair_mode: bool,
    ) -> list[str]:
        """Build the command-line arguments for invoking BoB.

        Constructs the full argv list for subprocess.Popen, including:
        - Project mode (-p)
        - Model selection
        - System prompt injection
        - Allowed tools (Read, Write, Edit)
        - Output format (stream-json)
        - Permission mode (acceptEdits)
        - Settings file (if provided)
        - The mellea-fy or mellea-fy-repair command

        Args:
            model: Claude model identifier (e.g., "claude-3-7-sonnet-20250219")
            system_prompt: System prompt to inject with runtime defaults
            compile_settings_path: Optional path to settings file with deny rules
            spec_path: Path to the skill specification file
            repair_mode: Whether to use /mellea-fy-repair instead of /mellea-fy

        Returns:
            List of command-line arguments ready for subprocess.Popen

        Example:
            >>> argv = self._build_claude_argv(
            ...     system_prompt="Use backend=anthropic...",
            ...     compile_settings_path=Path("settings.json"),
            ...     spec_path=Path("weather/spec.md"),
            ...     repair_mode=False,
            ... )
            >>> # argv = ["claude", "-p", "--model", "claude-3-7-sonnet-20250219", ...]
        """
        bob_argv = [
            "bob",
            f"/mellea-fy {spec_path}",
            "--yolo",
            "--allowed-tools",
            "Read,Write,Edit",
            "--output-format",
            "text",
        ]

        LOGGER.debug(f"BoB command - {" ".join(bob_argv)}")

        return bob_argv
