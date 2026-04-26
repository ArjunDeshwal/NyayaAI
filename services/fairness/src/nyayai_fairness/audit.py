"""Core fairness-audit pipeline.

Deterministic, classical. No Gemini. No LLM calls. No network.

Pipeline:

1. :func:`ingest.ingest` loads the dataset and emits proxy warnings.
2. Derive a binary decision from ``model_score`` (or use the outcome column).
   When ``train_baseline=True``, train an ephemeral
   :class:`sklearn.linear_model.LogisticRegression` on non-protected
   features, and use its ``predict_proba`` as the score column. The trained
   model is held only for the duration of the call --- never persisted,
   never logged, never sent to the LLM.
3. Standard Fairlearn metrics per protected attribute (wrappers).
4. Intersectional slicing per requested slice tuple.
5. India-context custom metrics:
     - Legacy SPLS (surname-proxy leakage AUC) + DLF (selection-rate
       by digital-literacy quartile).
     - RBI-aligned SPLS / LRB / DLF (priority-sector shortfall, rejection
       4/5ths-rule ratio, RBIH-FLF composite).
6. Counterfactual flips (only when ``train_baseline=True``; requires a real
   ``predict_proba``).
7. Root-cause analysis (only when ``train_baseline=True``).
8. Differential-privacy suppression for slices below k-anonymity.
9. Assemble a deterministic :class:`~nyayai_fairness.schemas.AuditResult`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any

import numpy as np
import pandas as pd

from nyayai_fairlearn_ext import (
    compute_counterfactual_flips,
    compute_group_fairness,
    compute_intersectional_fairness,
    compute_root_cause,
    digital_literacy_fairness,
    surname_proxy_leakage_score,
)
from nyayai_fairness.dp import DPConfig, protect_rate
from nyayai_fairness.ingest import ingest
from nyayai_fairness.schemas import (
    AuditRequest,
    AuditResult,
    CounterfactualReport,
    CustomIndiaMetrics,
    RootCauseReport,
    SliceReport,
)
from nyayai_taxonomy.rbi_metrics import (
    RBI_PSL_DEFAULT_TARGETS,
    compute_dlf as _compute_rbi_dlf,
    compute_lrb as _compute_rbi_lrb,
    compute_spls as _compute_rbi_spls,
)

# Default intersectional slices keyed by *column name convention* in the
# input DataFrame. Callers can override via AuditRequest.intersectional_slices.
_DEFAULT_SLICES: tuple[tuple[str, ...], ...] = (
    ("habitation", "gender", "caste_disclosed"),
    ("habitation", "religion"),
    ("mother_tongue", "typing_cadence_quartile"),
    ("gender",),
)


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def _determinism_hash(payload: dict[str, Any]) -> str:
    """SHA-256 of a canonically-serialized payload."""

    text = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _derive_decision(
    df: pd.DataFrame, score_col: str | None, outcome_col: str, threshold: float
) -> np.ndarray:
    if score_col is None:
        return df[outcome_col].astype(int).to_numpy()
    scores = df[score_col].astype(float).to_numpy()
    return (scores >= threshold).astype(int)


def _coerce_feature_frame(
    df: pd.DataFrame, exclude: set[str]
) -> pd.DataFrame:
    """Numeric / one-hot encoded feature frame for sklearn baselines.

    Mirrors the helper in :mod:`nyayai_orchestrator.tools.remediation_tool`
    so behaviour is identical between baseline training paths. Categoricals
    are one-hot encoded (drop_first to avoid collinearity); numerics pass
    through; NaNs are filled with column means then 0.
    """

    feat_cols = [c for c in df.columns if c not in exclude]
    X = df[feat_cols].copy()

    numeric_cols = X.select_dtypes(include=[np.number, "bool"]).columns.tolist()
    cat_cols = [c for c in feat_cols if c not in numeric_cols]
    if cat_cols:
        X = pd.get_dummies(X, columns=cat_cols, drop_first=True, dtype=float)
    X = X.astype(float)
    if X.isna().any().any():
        X = X.fillna(X.mean(numeric_only=True)).fillna(0.0)
    return X


def _train_baseline_model(
    df: pd.DataFrame,
    *,
    outcome_column: str,
    protected_columns: list[str],
    score_column: str | None,
    seed: int,
) -> tuple[Any, pd.DataFrame, np.ndarray]:
    """Train an ephemeral LogisticRegression and return (model, X, scores).

    Reuses the same coercion as the remediation tool. Protected columns,
    the outcome column, the (possibly user-provided) score column, and any
    obvious id columns are excluded from the feature universe.

    The trained model is intentionally not persisted by the caller --- it
    lives only for the duration of the audit call.
    """

    from sklearn.linear_model import LogisticRegression

    exclude: set[str] = {outcome_column, *protected_columns}
    if score_column:
        exclude.add(score_column)
    for c in df.columns:
        if c.lower() in {"applicant_id", "id", "row_id"}:
            exclude.add(c)

    X = _coerce_feature_frame(df, exclude=exclude)
    y = df[outcome_column].astype(int).to_numpy()
    if X.shape[1] == 0:
        raise ValueError(
            "train_baseline=True but no usable feature columns remained after "
            f"excluding {sorted(exclude)}"
        )

    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=seed,
        solver="liblinear",
    )
    model.fit(X, y)
    proba = model.predict_proba(X)
    if proba.ndim != 2 or proba.shape[1] < 2:
        raise ValueError(
            "baseline model did not return a 2-class predict_proba; "
            "is the outcome column truly binary?"
        )
    scores = proba[:, 1]
    return model, X, scores


def run_audit(req: AuditRequest) -> AuditResult:
    """Execute the full fairness pipeline and return a :class:`AuditResult`."""

    rng = np.random.default_rng(req.seed)
    ingest_out = ingest(
        req.dataset_uri,
        protected_columns=req.protected_columns,
        outcome_column=req.outcome_column,
        model_score_column=req.model_score_column,
    )
    df = ingest_out.df
    warnings: list[str] = list(ingest_out.warnings)

    y_true = df[req.outcome_column].astype(int).to_numpy()

    # Optional ephemeral baseline. Trained model is held in a local var only;
    # it is never persisted, never logged, never sent to the LLM.
    baseline_model: Any | None = None
    baseline_features: pd.DataFrame | None = None
    effective_score_column = req.model_score_column

    if req.train_baseline:
        try:
            baseline_model, baseline_features, scores = _train_baseline_model(
                df,
                outcome_column=req.outcome_column,
                protected_columns=req.protected_columns,
                score_column=req.model_score_column,
                seed=req.seed,
            )
            df = df.copy()
            df["__baseline_score"] = scores
            effective_score_column = "__baseline_score"
        except (ValueError, KeyError) as exc:
            warnings.append(
                f"train_baseline=True but training failed ({exc}); "
                "falling back to caller-provided model_score_column"
            )

    y_pred = _derive_decision(
        df, effective_score_column, req.outcome_column, req.decision_threshold
    )

    # ----- 1. Global selection rate
    global_metrics: dict[str, float] = {
        "n_rows": float(len(df)),
        "positive_rate_true": float(y_true.mean()),
        "positive_rate_pred": float(y_pred.mean()),
        "agreement": float((y_true == y_pred).mean()),
    }

    # ----- 2. Per-attribute group fairness (wrappers around Fairlearn).
    # Small subgroups (n < min_slice_n) are excluded from the aggregate to
    # avoid a 6-row group driving the worst-case DP ratio to 0. They are
    # re-surfaced as warnings so the Narrator can disclose the suppression.
    per_attribute_metrics: dict[str, dict[str, float]] = {}
    for col in req.protected_columns:
        gf = compute_group_fairness(
            y_true, y_pred, df[col], min_group_n=req.min_slice_n
        )
        if gf.excluded_groups:
            excluded_str = ", ".join(
                f"{name}({n})" for name, n in sorted(gf.excluded_groups.items())
            )
            warnings.append(
                f"attribute '{col}': {len(gf.excluded_groups)} subgroup(s) "
                f"excluded from aggregate (n < {req.min_slice_n}): {excluded_str}"
            )
        per_attribute_metrics[col] = {
            "demographic_parity_difference": gf.demographic_parity_difference,
            "demographic_parity_ratio": gf.demographic_parity_ratio,
            "equalized_odds_difference": gf.equalized_odds_difference,
            "equal_opportunity_difference": gf.equal_opportunity_difference,
            "false_positive_rate_difference": gf.false_positive_rate_difference,
        }
        dp_ratio = gf.demographic_parity_ratio
        if dp_ratio == dp_ratio and dp_ratio < 0.8:  # NaN-safe comparison
            warnings.append(
                f"attribute '{col}' fails the 4/5ths rule: DP ratio = "
                f"{dp_ratio:.3f} < 0.80"
            )

    # ----- 3. Intersectional slicing
    slice_specs = [tuple(s) for s in (req.intersectional_slices or _DEFAULT_SLICES)]
    slice_reports: list[SliceReport] = []
    dp_config = DPConfig(k_anonymity=req.dp_k_anonymity, seed=req.seed)

    for cols in slice_specs:
        missing = [c for c in cols if c not in df.columns]
        if missing:
            warnings.append(
                f"slice {cols} skipped: missing columns {missing}"
            )
            continue
        sens_df = df[list(cols)].astype(str)
        inter = compute_intersectional_fairness(
            y_true, y_pred, sens_df, min_slice_n=req.min_slice_n
        )
        for key, metrics in inter.metrics_by_slice.items():
            n = inter.n_by_slice[key]
            slice_key = {col: val for col, val in zip(cols, key, strict=True)}
            # Apply DP suppression / noise on rate metrics if small.
            dp_metrics: dict[str, float] = {}
            suppressed = False
            for mname, mval in metrics.items():
                protected_val, was_sup = protect_rate(float(mval), n, dp_config, rng)
                dp_metrics[mname] = protected_val
                suppressed = suppressed or was_sup
            slice_reports.append(
                SliceReport(
                    slice_key=slice_key,
                    n=n,
                    metrics=dp_metrics,
                    dp_protected=suppressed,
                )
            )

    # ----- 4. India-context custom metrics (legacy + RBI-aligned)
    india = _compute_india_custom(df, req, y_pred=y_pred)

    # ----- 5. Counterfactual flips (only when we have a real model in hand)
    counterfactual_report: CounterfactualReport | None = None
    root_cause_report: RootCauseReport | None = None
    if baseline_model is not None and baseline_features is not None:
        primary = req.protected_columns[0]
        if primary in df.columns:
            # Build a frame the model will accept: features + protected col.
            cf_X = baseline_features.copy()
            # If the protected col isn't already in the feature frame
            # (it shouldn't be — it was excluded), append it as a string for
            # value substitution. Counterfactual swaps the protected column
            # in-place; the model's predict_proba accepts the original
            # numeric frame, so we use the *features* frame directly and
            # carry a parallel protected-value series for substitution.
            try:
                counterfactual_report = _compute_counterfactual_for_audit(
                    model=baseline_model,
                    feature_frame=baseline_features,
                    df=df,
                    protected_column=primary,
                    seed=req.seed,
                    threshold=req.decision_threshold,
                    candidate_protected_columns=req.protected_columns,
                )
            except (ValueError, KeyError) as exc:
                warnings.append(
                    f"counterfactual flips skipped on '{primary}': {exc}"
                )
            try:
                root_cause_report = _compute_root_cause_for_audit(
                    model=baseline_model,
                    feature_frame=baseline_features,
                    df=df,
                    protected_column=primary,
                    y_pred=y_pred,
                    y_true=y_true,
                    seed=req.seed,
                    threshold=req.decision_threshold,
                )
            except (ValueError, KeyError) as exc:
                warnings.append(
                    f"root-cause analysis skipped on '{primary}': {exc}"
                )

    # ----- 6. Assemble result (deterministic).
    payload_for_hash: dict[str, Any] = {
        "global": global_metrics,
        "per_attribute": per_attribute_metrics,
        "slices": [
            {"key": s.slice_key, "n": s.n, "m": s.metrics, "dp": s.dp_protected}
            for s in slice_reports
        ],
        "india": india.model_dump(),
        "seed": req.seed,
    }
    if counterfactual_report is not None:
        payload_for_hash["counterfactual"] = counterfactual_report.model_dump()
    if root_cause_report is not None:
        payload_for_hash["root_cause"] = root_cause_report.model_dump()
    det_hash = _determinism_hash(payload_for_hash)

    return AuditResult(
        audit_id=f"audit-{uuid.uuid4().hex[:12]}",
        dataset_uri=req.dataset_uri,
        protected_columns=req.protected_columns,
        outcome_column=req.outcome_column,
        model_score_column=req.model_score_column,
        decision_threshold=req.decision_threshold,
        n_rows=len(df),
        global_metrics=global_metrics,
        per_attribute_metrics=per_attribute_metrics,
        slice_metrics=slice_reports,
        custom_india_metrics=india,
        counterfactual=counterfactual_report,
        root_cause=root_cause_report,
        warnings=warnings,
        determinism_hash=det_hash,
    )


def _compute_india_custom(
    df: pd.DataFrame, req: AuditRequest, *, y_pred: np.ndarray | None = None
) -> CustomIndiaMetrics:
    """Legacy SPLS+DLF + RBI-aligned SPLS / LRB / DLF.

    All three RBI metrics are best-effort: they depend on the dataset
    carrying the right columns (e.g. ``loan_amount`` for SPLS). Missing
    columns simply leave the slot at ``None``.
    """

    spls: dict[str, Any] | None = None
    dlf: dict[str, Any] | None = None
    rbi_spls: dict[str, Any] | None = None
    rbi_lrb: dict[str, Any] | None = None
    rbi_dlf: dict[str, Any] | None = None

    primary = req.protected_columns[0]
    # Features are everything other than the protected columns, outcome, and model score.
    feature_cols = [
        c
        for c in df.columns
        if c not in set(req.protected_columns)
        and c != req.outcome_column
        and c != req.model_score_column
    ]
    # Drop ids and free-text that don't contribute numerically.
    feature_cols = [c for c in feature_cols if c.lower() not in {"applicant_id", "id"}]
    if feature_cols:
        X = df[feature_cols].copy()
        spls_res = surname_proxy_leakage_score(X, df[primary], random_state=req.seed)
        spls = _to_jsonable(spls_res)

    # DLF: look for any column that fuzzy-matches "digital_literacy" / "typing_cadence".
    candidate = next(
        (c for c in df.columns if c.lower() in {"typing_cadence_quartile", "digital_literacy"}),
        None,
    )
    if candidate is not None:
        y_outcome = df[req.outcome_column].astype(int)
        dlf_res = digital_literacy_fairness(y_outcome, df[candidate])
        dlf = _to_jsonable(dlf_res)

    # ---- RBI-aligned variants ---------------------------------------------
    # RBI SPLS: needs an approved-loan amount column. We accept a few common
    # spellings; the dataset must also carry the protected column being
    # bucketed against PSL targets.
    amount_col = next(
        (
            c
            for c in df.columns
            if c.lower() in {"loan_amount", "amount", "approved_amount", "principal"}
        ),
        None,
    )
    if amount_col is not None and primary in df.columns:
        # Only count approved rows toward the loan-flow base.
        approved_mask = df[req.outcome_column].astype(int) == 1
        approved_amounts = df.loc[approved_mask, amount_col].fillna(0.0)
        approved_groups = df.loc[approved_mask, primary].astype(str)
        try:
            rbi_spls_res = _compute_rbi_spls(
                approved_amounts,
                approved_groups,
                target_pct_by_group=RBI_PSL_DEFAULT_TARGETS,
            )
            rbi_spls = _to_jsonable(rbi_spls_res)
        except ValueError:
            rbi_spls = None

    # RBI LRB: rejection rate by group, using the *predicted* decisions when
    # we have them, else the ground-truth outcomes (the latter conflates
    # model bias with sampling bias but at least gives a number on data-only
    # audits).
    if primary in df.columns:
        decisions_for_lrb = (
            y_pred
            if y_pred is not None
            else df[req.outcome_column].astype(int).to_numpy()
        )
        try:
            rbi_lrb_res = _compute_rbi_lrb(
                decisions_for_lrb,
                df[primary].astype(str),
                rejected_label=0,
            )
            rbi_lrb = _to_jsonable(rbi_lrb_res)
        except ValueError:
            rbi_lrb = None

    # RBI DLF composite: needs y_true + y_pred + group. y_score (the model
    # probabilities) is optional — when present, calibration uses Brier-gap.
    if primary in df.columns and y_pred is not None:
        y_true_arr = df[req.outcome_column].astype(int).to_numpy()
        score_col = (
            req.model_score_column
            if req.model_score_column in df.columns
            else (
                "__baseline_score" if "__baseline_score" in df.columns else None
            )
        )
        y_score_arr: pd.Series | None = (
            df[score_col] if score_col else None
        )
        try:
            rbi_dlf_res = _compute_rbi_dlf(
                y_true_arr,
                y_pred,
                df[primary].astype(str),
                y_score=y_score_arr,
            )
            rbi_dlf = _to_jsonable(rbi_dlf_res)
        except ValueError:
            rbi_dlf = None

    return CustomIndiaMetrics(
        spls=spls,
        dlf=dlf,
        lrb=None,
        rbi_spls=rbi_spls,
        rbi_lrb=rbi_lrb,
        rbi_dlf=rbi_dlf,
    )


# ---------------------------------------------------------------------------
# Counterfactual + root-cause helpers (only used when train_baseline=True)
# ---------------------------------------------------------------------------


class _BaselineModelWithProtected:
    """Adapter that lets the counterfactual / root-cause routines pass
    feature frames that *include* a protected-column column even though the
    underlying baseline model was trained on a frame without it.

    The adapter simply drops the protected column before calling the wrapped
    model's ``predict_proba``. This makes counterfactual flips on the
    baseline model trivially zero (the model literally cannot see the
    protected attribute), which is the *truthful* answer for a baseline
    that excludes it. Test fixtures inject their own model to demonstrate
    non-trivial flip rates.
    """

    def __init__(self, model: Any, training_columns: list[str]) -> None:
        self._model = model
        self._cols = list(training_columns)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        # Pass exactly the columns the model was trained on. Missing ones
        # are filled with zeros (one-hot dummies absent from this slice).
        df = pd.DataFrame(index=X.index)
        for col in self._cols:
            df[col] = X[col] if col in X.columns else 0.0
        return self._model.predict_proba(df)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        df = pd.DataFrame(index=X.index)
        for col in self._cols:
            df[col] = X[col] if col in X.columns else 0.0
        return self._model.predict(df)


def _build_cf_frame(
    feature_frame: pd.DataFrame,
    df: pd.DataFrame,
    protected_column: str,
) -> pd.DataFrame:
    """Concatenate the encoded feature frame with the raw protected column."""
    # Use the original encoded features but tag the protected column on so
    # counterfactual swap operates on a stable, read-back-able value.
    out = feature_frame.copy()
    out[protected_column] = df[protected_column].astype(str).reindex(out.index).to_numpy()
    return out


def _compute_counterfactual_for_audit(
    *,
    model: Any,
    feature_frame: pd.DataFrame,
    df: pd.DataFrame,
    protected_column: str,
    seed: int,
    threshold: float,
    candidate_protected_columns: list[str],
) -> CounterfactualReport:
    wrapper = _BaselineModelWithProtected(model, list(feature_frame.columns))
    X_cf = _build_cf_frame(feature_frame, df, protected_column)
    legal_values = sorted({str(v) for v in df[protected_column].dropna().unique()})
    if len(legal_values) < 2:
        raise ValueError(
            f"protected column '{protected_column}' has fewer than 2 levels "
            "after dropping nulls; counterfactual flips are undefined"
        )
    redact_cols = [c for c in candidate_protected_columns if c != protected_column]
    res = compute_counterfactual_flips(
        wrapper,
        X_cf,
        protected_column,
        legal_values,
        threshold=threshold,
        sample_size=200,
        seed=seed,
        redact_columns=redact_cols,
    )
    flip_rate_serialised = {
        f"{a}->{b}": v for (a, b), v in res.flip_rate_by_pair.items()
    }
    examples_serialised: list[dict[str, Any]] = []
    for ex in res.examples:
        examples_serialised.append(
            {
                "row_index": ex.row_index,
                "protected_value_before": ex.protected_value_before,
                "protected_value_after": ex.protected_value_after,
                "probability_before": ex.probability_before,
                "probability_after": ex.probability_after,
                "decision_before": ex.decision_before,
                "decision_after": ex.decision_after,
                "feature_snapshot": ex.feature_snapshot,
            }
        )
    return CounterfactualReport(
        protected_column=res.protected_column,
        protected_values=list(res.protected_values),
        flip_rate_by_pair=flip_rate_serialised,
        directional_flip_rate=res.directional_flip_rate,
        examples=examples_serialised,
        sample_size_used=res.sample_size_used,
    )


def _compute_root_cause_for_audit(
    *,
    model: Any,
    feature_frame: pd.DataFrame,
    df: pd.DataFrame,
    protected_column: str,
    y_pred: np.ndarray,
    y_true: np.ndarray,
    seed: int,
    threshold: float,
) -> RootCauseReport:
    wrapper = _BaselineModelWithProtected(model, list(feature_frame.columns))
    X_rc = _build_cf_frame(feature_frame, df, protected_column)
    res = compute_root_cause(
        wrapper,
        X_rc,
        y_pred,
        protected_column,
        n_repeats=10,
        seed=seed,
        top_k=8,
        threshold=threshold,
        y_true=y_true,
    )
    rankings_serialised: list[dict[str, Any]] = [
        {
            "feature_name": fc.feature_name,
            "contribution_to_disparity": fc.contribution_to_disparity,
            "contribution_to_accuracy": fc.contribution_to_accuracy,
        }
        for fc in res.feature_rankings
    ]
    return RootCauseReport(
        protected_column=res.protected_column,
        rankings=rankings_serialised,
        proxy_features=list(res.proxy_features),
        baseline_dp_gap=float(max(0.0, min(1.0, res.baseline_dp_gap))),
        baseline_accuracy=(
            None
            if (res.baseline_accuracy != res.baseline_accuracy)  # NaN
            else float(res.baseline_accuracy)
        ),
        proxy_threshold=res.proxy_threshold,
        n_repeats=res.n_repeats,
    )
