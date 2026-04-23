"""Deterministic eval harness for the NyayaAI prototype agents.

Runs every golden JSON under ``evals/goldens/`` against the configured
backend (default: stub) and asserts structural properties — never string
equality on LLM text. Exit code is non-zero on any failure so CI gates
correctly.

Usage::

    python evals/run_evals.py --backend stub
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

GOLDENS_DIR = Path(__file__).parent / "goldens"


def _load_goldens() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for p in sorted(GOLDENS_DIR.glob("*.json")):
        with p.open() as fh:
            data = json.load(fh)
        data["_path"] = str(p)
        items.append(data)
    return items


def _run_planner_golden(golden: dict[str, Any]) -> tuple[bool, str]:
    from nyayai_orchestrator.agents.planner import run_planner
    from nyayai_orchestrator.guardrails import NoOpArmor, NoOpSDP
    from nyayai_orchestrator.llm.factory import build_client
    from nyayai_orchestrator.schemas import AuditRequest

    req = AuditRequest.model_validate(golden["input"])
    plan = run_planner(
        req,
        client=build_client(),
        model="gemini-3.1-pro",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    exp = golden["expectations"]

    if exp.get("audit_id_matches_input") and plan.audit_id != req.audit_id:
        return False, f"audit_id mismatch: plan={plan.audit_id} req={req.audit_id}"
    if len(plan.steps) < exp.get("min_steps", 1):
        return False, f"too few steps: {len(plan.steps)}"
    if len(plan.slices) < exp.get("min_slices", 0):
        return False, f"too few slices: {len(plan.slices)}"
    if exp.get("requires_intersectional_slice"):
        if not any(len(s) >= 2 for s in plan.slices):
            return False, "no intersectional slice present"
    if plan.estimated_minutes > exp.get("estimated_minutes_max", 120):
        return False, f"estimated_minutes too high: {plan.estimated_minutes}"
    return True, "ok"


def _run_narrator_golden(golden: dict[str, Any]) -> tuple[bool, str]:
    from nyayai_orchestrator.agents.narrator import run_narrator
    from nyayai_orchestrator.guardrails import NoOpArmor, NoOpSDP
    from nyayai_orchestrator.llm.factory import build_client
    from nyayai_orchestrator.schemas import AuditResult

    result = AuditResult.model_validate(golden["input"])
    narrative = run_narrator(
        result,
        client=build_client(),
        model="gemini-3-flash",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    exp = golden["expectations"]

    if exp.get("audit_id_matches_input") and narrative.audit_id != result.audit_id:
        return False, "audit_id mismatch"
    if len(narrative.per_slice) < exp.get("min_per_slice_paragraphs", 1):
        return False, f"too few slice paragraphs: {len(narrative.per_slice)}"
    if len(narrative.recommendations) < exp.get("min_recommendations", 0):
        return False, "too few recommendations"
    needle = exp.get("require_disclaimer_substring")
    if needle and needle not in narrative.disclaimer:
        return False, f"disclaimer missing expected substring {needle!r}"
    return True, "ok"


RUNNERS = {
    "planner": _run_planner_golden,
    "narrator": _run_narrator_golden,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["stub", "vertex"], default="stub")
    args = parser.parse_args()

    os.environ["NYAYAI_LLM_BACKEND"] = args.backend

    goldens = _load_goldens()
    if not goldens:
        print("no goldens found", file=sys.stderr)
        return 2

    fails: list[tuple[str, str]] = []
    for g in goldens:
        runner = RUNNERS.get(g["agent"])
        if runner is None:
            fails.append((g["name"], f"no runner for agent {g['agent']}"))
            continue
        try:
            ok, reason = runner(g)
        except Exception as e:  # noqa: BLE001
            ok, reason = False, f"{type(e).__name__}: {e}"
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {g['name']} — {reason}")
        if not ok:
            fails.append((g["name"], reason))

    print(f"\n{len(goldens) - len(fails)}/{len(goldens)} passed.")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
