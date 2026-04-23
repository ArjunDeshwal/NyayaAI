"""Report rendering.

Takes an `AuditReport` (from `nyayai_orchestrator.schemas`) and produces:
  * JSON — machine-readable, canonical
  * HTML — human-readable, self-contained (inline CSS, no external assets)
  * PDF  — requires `weasyprint` extra; if missing, raises with a clear message

The HTML template is rubric-sensitive:
  * Explicit DPDP Rule 13 + EU AI Act annex — compliance-auditor requires this
  * Disparate-impact table with 4/5ths rule flagging
  * Per-slice paragraphs from the Narrator agent
  * Determinism hash in footer (hash-chain for audit log)

No LLM calls happen here.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from nyayai_orchestrator.schemas import AuditReport

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(
        enabled_extensions=("html", "xml", "j2"),
        default_for_string=True,
    ),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.3f}"


def _four_fifths_flag(ratio: float | None) -> str:
    if ratio is None:
        return "no-data"
    return "pass" if ratio >= 0.8 else "fail"


_env.filters["fmt_ratio"] = _format_ratio
_env.filters["ff_flag"] = _four_fifths_flag


def render_json(report: AuditReport) -> str:
    return report.model_dump_json(indent=2)


def render_html(report: AuditReport) -> str:
    template = _env.get_template("report.html.j2")
    return template.render(
        report=report,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def render_pdf(report: AuditReport) -> bytes:
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as e:
        # OSError is raised on macOS when libpango is not present. Treat
        # both as "PDF rendering unavailable" so callers can degrade
        # gracefully to HTML-only output.
        raise RuntimeError(
            "PDF rendering requires the `pdf` extra and system libs "
            "(pango, cairo): pip install nyayai-reporter[pdf] + brew install pango"
        ) from e

    html = render_html(report)
    try:
        return HTML(string=html).write_pdf()
    except OSError as e:
        raise RuntimeError(
            "PDF rendering failed (missing system library): "
            f"{e}. See README for pango/cairo install."
        ) from e


def write_all(report: AuditReport, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    json_path = out_dir / "report.json"
    json_path.write_text(render_json(report), encoding="utf-8")
    paths["json"] = json_path

    html_path = out_dir / "report.html"
    html_path.write_text(render_html(report), encoding="utf-8")
    paths["html"] = html_path

    try:
        pdf_bytes = render_pdf(report)
        pdf_path = out_dir / "report.pdf"
        pdf_path.write_bytes(pdf_bytes)
        paths["pdf"] = pdf_path
    except RuntimeError:
        pass

    return paths


def template_context_debug(report: AuditReport) -> dict[str, Any]:
    """For template authors — returns the exact dict passed to Jinja."""
    return {
        "report": report.model_dump(),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
