"""FastAPI gateway for the NyayaAI prototype.

Endpoints
---------
* GET  /health                      — liveness
* GET  /samples                     — list bundled demo datasets (MUDRA-Lite, UCI Adult, COMPAS)
* POST /audit/sample                — run audit against a bundled sample by id (no upload)
* POST /audit/sample-stream         — same, but stream per-agent timeline events (NDJSON)
* POST /audit/by-uri                — inline JSON, dataset readable on the server FS
* POST /audit/upload                — multipart CSV/parquet upload
* POST /audit/upload-stream         — multipart upload with a streamed agent timeline (NDJSON)
* GET  /reports/{audit_id}/{fmt}    — json | html | pdf

This service is a thin orchestration layer. All business logic lives in the
`services/fairness`, `services/orchestrator`, `services/reporter` packages.

Streaming protocol (NDJSON, content-type ``application/x-ndjson``)
------------------------------------------------------------------
Each event is a single JSON object on its own line, in this order:

    {"phase":"planner","status":"started"}
    {"phase":"planner","status":"done","elapsed_ms":4231}
    {"phase":"fairness","status":"started"}
    {"phase":"fairness","status":"done","elapsed_ms":823}
    ...
    {"phase":"complete","audit_id":"audit_xxx","report_html_url":"...",
     "overall_disparate_impact":0.424,"drift_level":"major"}

The client renders an animated agent timeline as events arrive and switches
to the result card once it sees ``"phase":"complete"``.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from pathlib import Path
from typing import Annotated, Any, AsyncIterator, Literal

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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from nyayai_orchestrator import run_audit
from nyayai_orchestrator.schemas import (
    AuditRequest,
    DatasetDescriptor,
    ModelCard,
)
from nyayai_reporter import write_all

from nyayai_api.samples import Sample, get_sample, list_samples
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


def _build_request(submission: AuditSubmission, dataset_path: Path) -> AuditRequest:
    df = _load_table(dataset_path)
    for col in submission.protected_columns + [submission.outcome_column]:
        if col not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Column '{col}' not in dataset (found: {list(df.columns)[:20]})",
            )

    audit_id = f"audit_{uuid.uuid4().hex[:12]}"
    return AuditRequest(
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


def _public_url(base_url: str, audit_id: str, fmt: str) -> str:
    """Compose a /reports/<id>/<fmt> URL on the public scheme.

    Behind Google's HTTPS front-end Starlette sees scheme=http; rewrite to
    https so the Flutter UI doesn't get mixed-content blocked.
    """
    base = base_url.rstrip("/")
    if base.startswith("http://") and ".run.app" in base:
        base = "https://" + base[len("http://") :]
    return f"{base}/reports/{audit_id}/{fmt}"


def _run_and_persist(
    settings: Settings,
    request: AuditRequest,
    base_url: str,
    *,
    emit: Any = None,
    train_baseline: bool = False,
) -> tuple[AuditResponse, Any]:
    """Run the orchestrator and persist artifacts. Returns (response, report).

    ``train_baseline=True`` is set for the /audit/sample paths where the
    bundled benchmark data has no caller-supplied model — the fairness
    engine trains an ephemeral LogisticRegression so the Counterfactual +
    Root-Cause agents can run.
    """
    kwargs: dict[str, Any] = {"train_baseline": train_baseline}
    if emit is not None:
        kwargs["emit"] = emit
    report = run_audit(request, **kwargs)

    out_dir = settings.artifacts_dir / request.audit_id
    paths = write_all(report, out_dir)

    response = AuditResponse(
        audit_id=request.audit_id,
        status="completed",
        overall_disparate_impact=report.result.overall_disparate_impact,
        drift_level=report.drift.level,
        report_json_url=_public_url(base_url, request.audit_id, "json"),
        report_html_url=_public_url(base_url, request.audit_id, "html"),
        report_pdf_url=(
            _public_url(base_url, request.audit_id, "pdf") if "pdf" in paths else None
        ),
    )
    return response, report


def _sample_to_submission(sample: Sample, *, override_goal: str | None,
                          override_regime: str | None) -> AuditSubmission:
    return AuditSubmission(
        dataset_name=sample.name.split(" (")[0],  # short name on the report
        dataset_uri=str(sample.parquet_path),
        goal=override_goal or sample.default_goal,
        regime=(override_regime or sample.default_regime),  # type: ignore[arg-type]
        model_id=sample.default_model_id,
        protected_columns=list(sample.protected_columns),
        outcome_column=sample.outcome_column,
        model_score_column=sample.model_score_column,
        requested_attributes=list(sample.default_requested_attributes),  # type: ignore[arg-type]
    )


# --- Streaming helper -------------------------------------------------------


async def _stream_audit(
    settings: Settings,
    request: AuditRequest,
    base_url: str,
    *,
    train_baseline: bool = False,
) -> AsyncIterator[bytes]:
    """Run ``run_audit`` in a thread and yield NDJSON events as they fire.

    Why a thread? ``run_audit`` is synchronous (Vertex SDK is sync). Running
    it in ``asyncio.to_thread`` keeps the event loop free to drain the queue
    we drip events into.
    """
    queue: asyncio.Queue[dict | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def emit(phase: str, status: str, **extra: Any) -> None:
        # Called from the worker thread; hand events back via the loop.
        evt = {"phase": phase, "status": status, **extra}
        loop.call_soon_threadsafe(queue.put_nowait, evt)

    response_holder: dict[str, AuditResponse] = {}
    error_holder: dict[str, BaseException] = {}

    def _worker() -> None:
        try:
            response, _report = _run_and_persist(
                settings, request, base_url,
                emit=emit, train_baseline=train_baseline,
            )
            response_holder["v"] = response
        except BaseException as exc:  # noqa: BLE001 — we want to surface anything
            error_holder["v"] = exc
        finally:
            # Sentinel signals the consumer that the worker is done.
            loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=_worker, daemon=True).start()

    # Initial heartbeat so clients can render an "audit started" timeline row
    # immediately, before the first agent fires.
    yield (json.dumps({"phase": "audit", "status": "started",
                       "audit_id": request.audit_id}) + "\n").encode("utf-8")

    while True:
        evt = await queue.get()
        if evt is None:
            break
        yield (json.dumps(evt) + "\n").encode("utf-8")

    if "v" in error_holder:
        exc = error_holder["v"]
        yield (json.dumps({"phase": "audit", "status": "error",
                           "error_type": type(exc).__name__,
                           "error_message": str(exc)[:500]}) + "\n").encode("utf-8")
        return

    response = response_holder["v"]
    yield (json.dumps({
        "phase": "complete",
        "status": "done",
        "audit_id": response.audit_id,
        "overall_disparate_impact": response.overall_disparate_impact,
        "drift_level": response.drift_level,
        "report_json_url": response.report_json_url,
        "report_html_url": response.report_html_url,
        "report_pdf_url": response.report_pdf_url,
    }) + "\n").encode("utf-8")


# --- Form helpers (used by both /upload and /upload-stream) ------------------


async def _persist_upload(file: UploadFile, settings: Settings) -> Path:
    filename = file.filename or "upload.csv"
    suffix = Path(filename).suffix or ".csv"
    upload_id = uuid.uuid4().hex[:12]
    dataset_path = settings.artifacts_dir / f"upload_{upload_id}{suffix}"

    body = await file.read()
    if len(body) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Upload > {settings.max_upload_mb}MB")
    dataset_path.write_bytes(body)
    return dataset_path


def _form_to_submission(
    *,
    dataset_name: str,
    goal: str,
    protected_columns: str,
    outcome_column: str,
    regime: str,
    model_id: str,
    model_score_column: str | None,
    dataset_path: Path,
) -> AuditSubmission:
    return AuditSubmission(
        dataset_name=dataset_name,
        dataset_uri=str(dataset_path),
        goal=goal,
        regime=regime,  # type: ignore[arg-type]
        model_id=model_id,
        protected_columns=[c.strip() for c in protected_columns.split(",") if c.strip()],
        outcome_column=outcome_column,
        model_score_column=model_score_column,
        requested_attributes=[],
    )


# --- App factory ------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="NyayaAI API",
        version="0.2.0",
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
        return {"status": "ok", "service": "nyayai-api", "version": "0.2.0"}

    # --- Sample dataset chooser --------------------------------------------

    @app.get("/samples")
    def get_samples() -> list[dict]:
        return list_samples()

    @app.post("/audit/sample", response_model=AuditResponse)
    def audit_sample(
        body: dict,
        request: Request,
    ) -> AuditResponse:
        sample_id = body.get("sample_id") or ""
        sample = get_sample(sample_id)
        if sample is None:
            raise HTTPException(status_code=404, detail=f"Unknown sample id: {sample_id!r}")
        if not sample.parquet_path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"Sample {sample_id!r} parquet missing at {sample.parquet_path}",
            )
        submission = _sample_to_submission(
            sample,
            override_goal=body.get("goal"),
            override_regime=body.get("regime"),
        )
        request_obj = _build_request(submission, sample.parquet_path)
        # Sample audits train an ephemeral baseline so the new Counterfactual
        # + Root-Cause agents have a real predict_proba to work against.
        response, _ = _run_and_persist(
            settings, request_obj, str(request.base_url), train_baseline=True,
        )
        return response

    @app.post("/audit/sample-stream")
    async def audit_sample_stream(body: dict, request: Request) -> StreamingResponse:
        sample_id = body.get("sample_id") or ""
        sample = get_sample(sample_id)
        if sample is None:
            raise HTTPException(status_code=404, detail=f"Unknown sample id: {sample_id!r}")
        if not sample.parquet_path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"Sample {sample_id!r} parquet missing at {sample.parquet_path}",
            )
        submission = _sample_to_submission(
            sample,
            override_goal=body.get("goal"),
            override_regime=body.get("regime"),
        )
        request_obj = _build_request(submission, sample.parquet_path)
        return StreamingResponse(
            _stream_audit(
                settings, request_obj, str(request.base_url),
                train_baseline=True,
            ),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # --- Inline / by-URI ----------------------------------------------------

    @app.post("/audit/by-uri", response_model=AuditResponse)
    def audit_by_uri(submission: AuditSubmission, request: Request) -> AuditResponse:
        dataset_path = Path(submission.dataset_uri)
        if not dataset_path.exists():
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_path}")
        request_obj = _build_request(submission, dataset_path)
        response, _ = _run_and_persist(settings, request_obj, str(request.base_url))
        return response

    # --- Multipart upload (sync) -------------------------------------------

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
        dataset_path = await _persist_upload(file, settings)
        submission = _form_to_submission(
            dataset_name=dataset_name, goal=goal,
            protected_columns=protected_columns, outcome_column=outcome_column,
            regime=regime, model_id=model_id,
            model_score_column=model_score_column, dataset_path=dataset_path,
        )
        request_obj = _build_request(submission, dataset_path)
        response, _ = _run_and_persist(settings, request_obj, str(request.base_url))
        return response

    # --- Multipart upload (streamed timeline) ------------------------------

    @app.post("/audit/upload-stream")
    async def audit_upload_stream(
        request: Request,
        file: Annotated[UploadFile, File()],
        dataset_name: Annotated[str, Form()],
        goal: Annotated[str, Form()],
        protected_columns: Annotated[str, Form(description="Comma-separated")],
        outcome_column: Annotated[str, Form()],
        regime: Annotated[Literal["DPDP", "EU_AI_ACT", "RBI"], Form()] = "DPDP",
        model_id: Annotated[str, Form()] = "unknown",
        model_score_column: Annotated[str | None, Form()] = None,
    ) -> StreamingResponse:
        dataset_path = await _persist_upload(file, settings)
        submission = _form_to_submission(
            dataset_name=dataset_name, goal=goal,
            protected_columns=protected_columns, outcome_column=outcome_column,
            regime=regime, model_id=model_id,
            model_score_column=model_score_column, dataset_path=dataset_path,
        )
        request_obj = _build_request(submission, dataset_path)
        return StreamingResponse(
            _stream_audit(settings, request_obj, str(request.base_url)),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # --- Reports ------------------------------------------------------------

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
