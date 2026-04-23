"""FastAPI gateway for the NyayaAI prototype.

Endpoints
---------
* GET  /health                      — liveness
* POST /audit/by-uri                — inline JSON, dataset readable on the server FS
* POST /audit/upload                — multipart CSV/parquet upload
* GET  /reports/{audit_id}/{fmt}    — json | html | pdf

This service is a thin orchestration layer. All business logic lives in the
`services/fairness`, `services/orchestrator`, `services/reporter` packages.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated, Literal

import pandas as pd
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from nyayai_orchestrator import run_audit
from nyayai_orchestrator.schemas import (
    AuditRequest,
    DatasetDescriptor,
    ModelCard,
)
from nyayai_reporter import write_all

from nyayai_api.schemas import AuditResponse, AuditSubmission
from nyayai_api.settings import Settings, get_settings
from nyayai_api.ui import INDEX_HTML


def _load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if path.suffix.lower() in (".csv", ".tsv"):
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        return pd.read_csv(path, sep=sep)
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=f"Unsupported extension {path.suffix}; expected .parquet/.csv/.tsv",
    )


def _run(
    settings: Settings,
    submission: AuditSubmission,
    dataset_path: Path,
    base_url: str,
) -> AuditResponse:
    df = _load_table(dataset_path)
    for col in submission.protected_columns + [submission.outcome_column]:
        if col not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Column '{col}' not in dataset (found: {list(df.columns)[:20]})",
            )

    audit_id = f"audit_{uuid.uuid4().hex[:12]}"

    request = AuditRequest(
        audit_id=audit_id,
        goal=submission.goal,
        regime=submission.regime,
        model=ModelCard(model_id=submission.model_id, task=submission.model_task),
        dataset=DatasetDescriptor(
            name=submission.dataset_name,
            row_count=len(df),
            columns=list(df.columns),
            candidate_protected_columns=submission.protected_columns,
            source_uri=str(dataset_path),
            outcome_column=submission.outcome_column,
            model_score_column=submission.model_score_column,
        ),
        requested_attributes=submission.requested_attributes,
    )

    report = run_audit(request)

    out_dir = settings.artifacts_dir / audit_id
    paths = write_all(report, out_dir)

    def url(fmt: str) -> str:
        return f"{base_url.rstrip('/')}/reports/{audit_id}/{fmt}"

    return AuditResponse(
        audit_id=audit_id,
        status="completed",
        overall_disparate_impact=report.result.overall_disparate_impact,
        drift_level=report.drift.level,
        report_json_url=url("json"),
        report_html_url=url("html"),
        report_pdf_url=url("pdf") if "pdf" in paths else None,
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="NyayaAI API",
        version="0.1.0",
        description="Agentic, India-aware bias auditor — HTTP gateway.",
    )
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "nyayai-api", "version": "0.1.0"}

    @app.post("/audit/by-uri", response_model=AuditResponse)
    def audit_by_uri(submission: AuditSubmission, request: Request) -> AuditResponse:
        dataset_path = Path(submission.dataset_uri)
        if not dataset_path.exists():
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_path}")
        return _run(settings, submission, dataset_path, str(request.base_url))

    @app.post("/audit/upload", response_model=AuditResponse)
    async def audit_upload(
        request: Request,
        file: Annotated[UploadFile, File()],
        dataset_name: Annotated[str, Form()],
        goal: Annotated[str, Form()],
        protected_columns: Annotated[str, Form(description="Comma-separated")],
        outcome_column: Annotated[str, Form()],
        regime: Annotated[Literal["DPDP", "EU_AI_ACT", "RBI"], Form()] = "DPDP",
        model_id: Annotated[str, Form()] = "unknown",
        model_score_column: Annotated[str | None, Form()] = None,
    ) -> AuditResponse:
        filename = file.filename or "upload.csv"
        suffix = Path(filename).suffix or ".csv"
        upload_id = uuid.uuid4().hex[:12]
        dataset_path = settings.artifacts_dir / f"upload_{upload_id}{suffix}"

        body = await file.read()
        if len(body) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"Upload > {settings.max_upload_mb}MB")
        dataset_path.write_bytes(body)

        submission = AuditSubmission(
            dataset_name=dataset_name,
            dataset_uri=str(dataset_path),
            goal=goal,
            regime=regime,
            model_id=model_id,
            protected_columns=[c.strip() for c in protected_columns.split(",") if c.strip()],
            outcome_column=outcome_column,
            model_score_column=model_score_column,
            requested_attributes=[],
        )
        return _run(settings, submission, dataset_path, str(request.base_url))

    @app.get("/reports/{audit_id}/{fmt}")
    def get_report(audit_id: str, fmt: Literal["json", "html", "pdf"]) -> FileResponse:
        if not audit_id.startswith("audit_") or "/" in audit_id or ".." in audit_id:
            raise HTTPException(status_code=400, detail="Invalid audit_id")
        out_dir = settings.artifacts_dir / audit_id
        file_path = out_dir / f"report.{fmt}"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        media_type = {
            "json": "application/json",
            "html": "text/html",
            "pdf": "application/pdf",
        }[fmt]
        return FileResponse(file_path, media_type=media_type)

    @app.exception_handler(ValueError)
    def _value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return app


app = create_app()
