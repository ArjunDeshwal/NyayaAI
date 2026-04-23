"""Command-line entry point for the fairness service.

Usage::

    python -m nyayai_fairness.cli audit data/mudra-lite.parquet \\
      --protected caste_disclosed,gender,habitation \\
      --outcome approved \\
      --model-score model_score \\
      --report-out report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nyayai_fairness.audit import run_audit
from nyayai_fairness.schemas import AuditRequest


def _cmd_audit(args: argparse.Namespace) -> int:
    protected = [c.strip() for c in args.protected.split(",") if c.strip()]
    req = AuditRequest(
        dataset_uri=str(args.dataset),
        protected_columns=protected,
        outcome_column=args.outcome,
        model_score_column=args.model_score,
        decision_threshold=args.threshold,
        seed=args.seed,
        dp_k_anonymity=args.k_anonymity,
        min_slice_n=args.min_slice_n,
    )
    result = run_audit(req)
    payload = result.model_dump(mode="json")
    if args.report_out is not None:
        out = Path(args.report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, default=str))
        print(f"Wrote report to {out}")
    else:
        json.dump(payload, sys.stdout, indent=2, default=str)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nyayai_fairness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser("audit", help="Run a fairness audit on a dataset.")
    p_audit.add_argument("dataset", help="Path to parquet or CSV.")
    p_audit.add_argument(
        "--protected",
        required=True,
        help="Comma-separated list of protected column names.",
    )
    p_audit.add_argument("--outcome", required=True, help="Ground-truth binary column.")
    p_audit.add_argument("--model-score", default=None, help="Model score column (optional).")
    p_audit.add_argument("--threshold", type=float, default=0.5)
    p_audit.add_argument("--seed", type=int, default=42)
    p_audit.add_argument("--k-anonymity", type=int, default=100)
    p_audit.add_argument("--min-slice-n", type=int, default=1)
    p_audit.add_argument("--report-out", default=None, help="Write JSON report here.")
    p_audit.set_defaults(func=_cmd_audit)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
