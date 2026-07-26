#!/usr/bin/env python3
"""Mellea Skills Compiler — Ingest an OpenClaw SKILL.md and certify it.

Pipeline:
  1. Parse SKILL.md (YAML frontmatter + markdown body)
  2. Classify tool sensitivity tier (lookup table, no regex)
  3. Compose use-case description for Nexus
  4. Nexus risk identification → policy manifest
  5. Compliance classification
  6. Certification report
"""

from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Optional

from mellea_skills_compiler.certification import policy, skill_to_use_case
from mellea_skills_compiler.certification.classification import (
    classify_governance_requirements,
    classify_skill_sensitivity,
)
from mellea_skills_compiler.certification.data import get_data_path
from mellea_skills_compiler.certification.report import generate_certification_report
from mellea_skills_compiler.enums import InferenceEngineType
from mellea_skills_compiler.inference import InferenceService
from mellea_skills_compiler.toolkit.file_utils import parse_spec_file
from mellea_skills_compiler.toolkit.logging import configure_logger


LOGGER: Logger = configure_logger()


def ingest_one(
    spec_path: Path,
    dry_run: bool = False,
    risk_model: Optional[str] = None,
    inference_engine_type: InferenceEngineType = InferenceEngineType.OLLAMA,
) -> None:
    """Risk Analysis and Policy Generation Pipeline for Mellea skill

    Args:
        skill_name (str): Mellea Skill spec path.
        dry_run (bool, optional): Preview without making LLM calls. Defaults to False.
        risk_model (Optional[str], optional): Model to use for Risk and Action Identification. The `inference_engine` param must support the model. If set to None, the default model for the inference engine will be used.
        inference_engine (InferenceEngineType, optional): Service to use for LLM inference. Defaults to InferenceEngineType.OLLAMA.
    """

    # Verify that spec file ends in a .md extension
    if spec_path.suffix != ".md":
        raise ValueError(
            f"invalid spec file - {spec_path}. Only markdown (.md) file is supported."
        )

    # Verify the spec file exists
    if spec_path.exists():
        # Verify that given path is not a directory
        if spec_path.is_dir():
            raise ValueError(
                "The specified path is a directory. Please note that the compile command only accepts a skill spec file in .md format."
            )
    else:
        raise FileNotFoundError(f"Skill spec file not found: {spec_path}")

    LOGGER.info("=== MelleaSkills — SKILL.md Ingestion ===")
    LOGGER.info("")

    # ── Step 1: Parse ───────────────────────────────────────────────
    LOGGER.info("Step 1: Parsing %s...", spec_path.name)
    parsed = parse_spec_file(spec_path)
    fm = parsed["frontmatter"]
    LOGGER.info("  Name: %s", fm.get("name", "unknown"))
    LOGGER.info("  Description: %.100s", fm.get("description", ""))
    LOGGER.info("  Tools: %s", fm.get("allowed-tools", []))
    LOGGER.info("")

    # ── Step 2: Sensitivity classification ──────────────────────────
    LOGGER.info("Step 2: Tool sensitivity classification...")
    sensitivity = classify_skill_sensitivity(
        fm.get("allowed-tools", []), parsed["body"]
    )
    LOGGER.info("  Tier: %s", sensitivity["tier_display"])
    LOGGER.info("  Operations: %s", sensitivity["operations"])
    if sensitivity["capabilities"]:
        LOGGER.info("  Capabilities: %s", sensitivity["capabilities"])
    LOGGER.info("")

    # ── Step 3: Compose use-case description ────────────────────────
    use_case = skill_to_use_case(parsed, sensitivity)
    LOGGER.info("Step 3: Use-case description:")
    LOGGER.info("  %s", use_case)

    if dry_run:
        LOGGER.info("=== Dry-run complete ===")
        return

    # load and create ai atlas nexus instance
    from ai_atlas_nexus.library import AIAtlasNexus

    nexus_data_path = get_data_path()
    nexus = AIAtlasNexus(base_dir=nexus_data_path)

    # ── Step 4: Nexus risk identification ───────────────────────────
    LOGGER.info("Step 4: Identifying risks via AI Atlas Nexus...")

    # Certification artifacts go into the skill's audit/ directory
    audit_dir = (
        spec_path.parent / f"audit_{datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}"
    )
    audit_dir.mkdir(exist_ok=True)

    # Genereate policy manifest
    manifest = policy.generate_policy_manifest(
        use_case, nexus, inference_engine=InferenceService.risk_engine(risk_model, inference_engine_type)
    )
    manifest_path = audit_dir / "policy_manifest.json"
    manifest.to_json(manifest_path)

    # Generate policy markdown
    policy_md = policy.generate_policy_markdown(manifest)
    policy_path = audit_dir / "POLICY.md"
    policy_path.write_text(policy_md)

    LOGGER.info("Policy manifest: %s", manifest_path)
    LOGGER.info("Policy document: %s", policy_path)

    # ── Step 5: Compliance classification ───────────────────────────
    LOGGER.info("Step 5: Compliance classification...")
    compliance = classify_governance_requirements(manifest, nexus)
    counts = compliance.counts
    LOGGER.info(
        "  AUTOMATED=%d  PARTIAL=%d  MANUAL=%d  (total=%d)",
        counts["AUTOMATED"],
        counts["PARTIAL"],
        counts["MANUAL"],
        sum(counts.values()),
    )
    LOGGER.info("")

    # ── Step 6: Certification report ────────────────────────────────
    LOGGER.info("Step 6: Generating certification report...")
    report: str = generate_certification_report(
        manifest,
        compliance,
        audit_trail=[],
        audit_path="(no runtime audit — static analysis only)",
    )
    report_path: Path = audit_dir / "CERTIFICATION.md"
    report_path.write_text(data=report)
    LOGGER.info("  Artifact: %s", report_path.name)
    LOGGER.info("")

    # ── Summary ─────────────────────────────────────────────────────
    skill_name = fm.get("name", "unknown")
    LOGGER.info("=== Summary: %s ===", skill_name)
    LOGGER.info(
        "  Sensitivity: %s | Operations: %s",
        sensitivity["tier_display"],
        sensitivity["operations"],
    )
    LOGGER.info(
        "  Guardian risks: %d | Governance actions: %d",
        len(manifest.risks),
        len(manifest.governance_actions),
    )
    LOGGER.info(
        "  Compliance: AUTOMATED=%d PARTIAL=%d MANUAL=%d",
        counts["AUTOMATED"],
        counts["PARTIAL"],
        counts["MANUAL"],
    )
