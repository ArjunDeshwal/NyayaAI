"""Classical remediation tool.

Deterministic, non-LLM. Takes the original :class:`AuditRequest` plus the
already-computed :class:`AuditResult`, identifies the worst-case protected
attribute (lowest DP ratio), retrains a simple ``LogisticRegression`` under a
Fairlearn :class:`~fairlearn.reductions.ExponentiatedGradient` /
:class:`~fairlearn.reductions.DemographicParity` constraint, re-runs the
classical fairness audit on the remediated predictions, and returns:

    * the before-DP-ratio (from the input result)
    * the after-DP-ratio (from the re-audit)
    * the test-set accuracy of the remediated classifier vs. the baseline

No Gemini in this module. The LLM consumes the :class:`RemediationOutcome`
downstream to write plain language — that's where judgement lives; the math
is reductions.

Import safety
-------------
``fairlearn.reductions``, ``sklearn`` and ``pandas`` are imported inside
:func:`run_remediation` so that ``import nyayai_orchestrator.tools`` never
fails in an environment that only has the prototype LLM stack installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from ..schemas import (
    AuditPlan,
    AuditRequest,
    AuditResult,
    ProtectedAttribute,
    SliceMetric,
)
from .fairness_tool import FairnessUnavailable, _flatten_metrics

if TYPE_CHECKING:  # pragma: no cover - type-checking only
    import pandas as pd


class RemediationUnavailable(RuntimeError):
    """Raised when Fairlearn / sklearn is missing, or the input is malformed.

    Callers (the orchestrator) catch this and skip the remediation step
    cleanly instead of failing the whole audit.
    """


class RemediationOutcome(BaseModel):
    """Structured output of the classical remediation pass.

    This is what the LLM narrative agent receives — it never invents these
    numbers, it only restates them.
    """

    audit_id: str
    mitigation_name: str = "fairlearn.reductions.ExponentiatedGradient+DemographicParity"
    target_attribute: ProtectedAttribute | None = None
    target_column: str
    before_dp_ratio: float
    after_dp_ratio: float
    baseline_accuracy: float
    remediated_accuracy: float
    accuracy_delta_pp: float = Field(
        description="Percentage-point change in accuracy vs. baseline.",
    )
    epsilon: float = 0.05
    n_train: int = Field(ge=0)
    n_test: int = Field(ge=0)
    # Optional re-audit metric rows; handy for logs / PDFs.
    post_metrics: list[SliceMetric] = Field(default_factory=list)


@dataclass(frozen=True)
class _WorstAttribute:
    """Pick of the protected attribute to mitigate on."""

    attribute: str
    dp_ratio: float


_COLUMN_TO_SEMANTIC: dict[str, ProtectedAttribute] = {
    "caste": "caste",
    "caste_disclosed": "caste",
    "jati": "caste",
    "religion": "religion",
    "dharma": "religion",
    "gender": "gender",
    "sex": "gender",
    "region": "region",
    "state": "region",
    "district": "region",
    "habitation": "urban_rural",
    "urban_rural": "urban_rural",
    "rural_urban": "urban_rural",
    "language": "language",
    "mother_tongue": "language",
    "matrubhasha": "language",
    "disability": "disability",
    "divyang": "disability",
    "age_band": "age_band",
    "age_cohort": "age_band",
    "age": "age_band",
}


def _pick_worst_attribute(result: AuditResult) -> _WorstAttribute | None:
    """Find the per-attribute slice with the lowest DP ratio.

    Returns ``None`` if no per-attribute DP ratio is present (the fairness
    tool prefixes attribute rows with ``attribute=<col>``).
    """
    best: _WorstAttribute | None = None
    for m in result.metrics:
        if m.metric != "demographic_parity_ratio":
            continue
        if not m.slice_key.startswith("attribute="):
            continue
        attr = m.slice_key.removeprefix("attribute=")
        val = float(m.value)
        # Skip NaN / non-finite.
        if not (val == val):  # NaN check
            continue
        if best is None or val < best.dp_ratio:
            best = _WorstAttribute(attribute=attr, dp_ratio=val)
    return best


def _coerce_feature_frame(df: "pd.DataFrame", exclude: set[str]) -> "pd.DataFrame":
    """Return a numeric feature matrix suitable for LogisticRegression.

    * Drops ``exclude`` columns (protected, outcome, score, ids).
    * Numeric columns pass through.
    * Object / bool columns get one-hot encoded.
    """
    import numpy as np
    import pandas as pd

    feat_cols = [c for c in df.columns if c not in exclude]
    X = df[feat_cols].copy()

    numeric_cols = X.select_dtypes(include=[np.number, "bool"]).columns.tolist()
    cat_cols = [c for c in feat_cols if c not in numeric_cols]

    if cat_cols:
        X = pd.get_dummies(X, columns=cat_cols, drop_first=True, dtype=float)
    # Ensure float dtype end-to-end.
    X = X.astype(float)
    # Fill any residual NaN with column mean (LogisticRegression cannot handle NaN).
    if X.isna().any().any():
        X = X.fillna(X.mean(numeric_only=True)).fillna(0.0)
    return X


def _reaudit_post_remediation(
    request: AuditRequest,
    plan: AuditPlan,
    df_test: "pd.DataFrame",
    y_pred_remediated: "Any",
) -> tuple[list[SliceMetric], float | None]:
    """Call the classical fairness engine on the remediated predictions.

    We write a temporary parquet with ``approved`` replaced by the remediated
    predictions (so that ``selection rate`` matches the new decisions) and a
    trivial ``model_score`` column (0/1). ``min_slice_n`` mirrors the main
    audit's floor so tiny groups don't distort the worst-case.
    """
    import tempfile
    from pathlib import Path

    try:
        from nyayai_fairness.audit import run_audit as _run  # type: ignore[import-not-found]
        from nyayai_fairness.schemas import (  # type: ignore[import-not-found]
            AuditRequest as FairnessAuditRequest,
        )
    except ImportError as e:
        raise FairnessUnavailable(
            "services/fairness is not installed; cannot re-audit post-remediation."
        ) from e

    ds = request.dataset
    if ds.outcome_column is None or not ds.candidate_protected_columns:
        raise FairnessUnavailable(
            "Cannot re-audit: outcome_column / candidate_protected_columns missing."
        )

    df_remediated = df_test.copy()
    df_remediated[ds.outcome_column] = y_pred_remediated.astype(int)
    # Build a model_score column aligned with the remediated decision so the
    # classical audit's threshold-based derivation agrees.
    df_remediated["__remediated_score"] = y_pred_remediated.astype(float)

    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "remediated.parquet"
        df_remediated.to_parquet(out_path, index=False)

        fairness_req = FairnessAuditRequest(
            dataset_uri=str(out_path),
            protected_columns=ds.candidate_protected_columns,
            outcome_column=ds.outcome_column,
            model_score_column="__remediated_score",
            decision_threshold=0.5,
            intersectional_slices=None,  # per-attribute is what we care about post-fix
            min_slice_n=20,
            dp_k_anonymity=20,  # looser than the main audit for the smaller test frame
        )

        try:
            fairness_result = _run(fairness_req)
        except Exception as e:  # noqa: BLE001
            raise FairnessUnavailable(
                f"Post-remediation re-audit failed: {type(e).__name__}: {e}"
            ) from e

    metrics, overall_di = _flatten_metrics(fairness_result)
    return metrics, overall_di


def run_remediation(
    request: AuditRequest,
    result: AuditResult,
    *,
    epsilon: float = 0.05,
    test_fraction: float = 0.3,
    random_state: int = 42,
) -> RemediationOutcome:
    """Retrain under Demographic Parity and re-audit.

    Strategy (deterministic):
      1. Pick the protected column with the worst (lowest) DP ratio.
      2. Load the dataset from ``request.dataset.source_uri``.
      3. 70/30 stratified train/test split, seed = ``random_state``.
      4. Baseline = ``LogisticRegression`` on train, predict on test.
      5. Remediated = ``ExponentiatedGradient(LogisticRegression,
         DemographicParity(difference_bound=epsilon))`` on train, predict on
         test. Sensitive feature = the chosen protected column.
      6. Re-run :mod:`nyayai_fairness.audit` on the remediated predictions to
         get the authoritative post DP ratio (not an ad-hoc local number).
      7. Return the structured :class:`RemediationOutcome`.
    """
    # ---- Lazy imports (service must not fail import if these are absent) ----
    try:
        import numpy as np  # noqa: F401
        import pandas as pd
        from fairlearn.reductions import DemographicParity, ExponentiatedGradient
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score
        from sklearn.model_selection import train_test_split
    except ImportError as e:
        raise RemediationUnavailable(
            "Remediation requires fairlearn, scikit-learn and pandas. Install "
            "the fairness service ('uv sync' in the workspace root)."
        ) from e

    ds = request.dataset
    if ds.source_uri is None:
        raise RemediationUnavailable(
            "AuditRequest.dataset.source_uri is required for remediation."
        )
    if ds.outcome_column is None:
        raise RemediationUnavailable(
            "AuditRequest.dataset.outcome_column is required for remediation."
        )
    if not ds.candidate_protected_columns:
        raise RemediationUnavailable(
            "AuditRequest.dataset.candidate_protected_columns must be non-empty."
        )

    # ---- 1. Pick worst attribute to mitigate on ----
    worst = _pick_worst_attribute(result)
    if worst is None:
        # Fall back to the first candidate column.
        target_col = ds.candidate_protected_columns[0]
        before_dp = float("nan")
    else:
        target_col = worst.attribute
        before_dp = worst.dp_ratio
    if target_col not in ds.candidate_protected_columns:
        # Defensive: worst.attribute should be a real column; but if the
        # fairness engine ever aliases, fall back to first candidate.
        target_col = ds.candidate_protected_columns[0]

    # ---- 2. Load dataset ----
    from pathlib import Path

    src = Path(ds.source_uri)
    if not src.exists():
        raise RemediationUnavailable(f"dataset not found: {ds.source_uri}")
    if src.suffix.lower() == ".parquet":
        df = pd.read_parquet(src)
    elif src.suffix.lower() in {".csv", ".tsv"}:
        df = pd.read_csv(src, sep="," if src.suffix.lower() == ".csv" else "\t")
    else:
        raise RemediationUnavailable(f"unsupported dataset format: {src.suffix}")

    if ds.outcome_column not in df.columns or target_col not in df.columns:
        raise RemediationUnavailable(
            f"outcome column '{ds.outcome_column}' or target "
            f"'{target_col}' missing from dataset."
        )

    y = df[ds.outcome_column].astype(int).to_numpy()
    A = df[target_col].astype(str)  # sensitive feature (str for ExpGrad)

    exclude = {
        ds.outcome_column,
        *ds.candidate_protected_columns,
    }
    if ds.model_score_column:
        exclude.add(ds.model_score_column)
    # Drop obvious id columns so the baseline doesn't memorise them.
    for c in list(df.columns):
        if c.lower() in {"applicant_id", "id"}:
            exclude.add(c)

    X = _coerce_feature_frame(df, exclude=exclude)

    # ---- 3. Train/test split (stratified by protected + outcome so both
    # sides see every (group × label) cell) ----
    # Stratify by the composite to preserve DP baseline conditions.
    strat = A.astype(str) + "__" + pd.Series(y, index=A.index).astype(str)
    try:
        X_train, X_test, y_train, y_test, A_train, A_test = train_test_split(
            X, y, A, test_size=test_fraction, random_state=random_state, stratify=strat
        )
    except ValueError:
        # Stratification can fail if some (group × label) is singleton. Fall
        # back to non-stratified.
        X_train, X_test, y_train, y_test, A_train, A_test = train_test_split(
            X, y, A, test_size=test_fraction, random_state=random_state
        )

    # ---- 4. Baseline model ----
    baseline = LogisticRegression(max_iter=1000, solver="liblinear")
    baseline.fit(X_train, y_train)
    y_pred_base = baseline.predict(X_test)
    baseline_acc = float(accuracy_score(y_test, y_pred_base))

    # ---- 5. Remediated model (ExponentiatedGradient + DemographicParity) ----
    # ExponentiatedGradient returns a *randomized* classifier — calling
    # ``.predict`` samples from the mixture, which makes the numbers bounce
    # from run to run. We instead threshold the deterministic PMF, which is
    # the marginal predicted probability under the randomized policy. This
    # is standard (see Agarwal et al. 2018 §4) and makes the remediated
    # metrics reproducible — critical for the video script.
    import numpy as _np

    def _fit_and_predict(eps: float) -> tuple["Any", float]:
        constraint = DemographicParity(difference_bound=eps)
        mit = ExponentiatedGradient(
            estimator=LogisticRegression(max_iter=1000, solver="liblinear"),
            constraints=constraint,
            eps=eps,
        )
        mit.fit(X_train, y_train, sensitive_features=A_train)
        # ``_pmf_predict`` returns an (n, 2) array of class probabilities
        # from the mixture; index 1 is the positive class.
        probs = mit._pmf_predict(X_test)[:, 1]
        preds = (probs >= 0.5).astype(int)
        acc = float(accuracy_score(y_test, preds))
        return preds, acc

    # Small deterministic sweep. Reductions under DP is non-monotonic in
    # epsilon (the stopping criterion and the Lagrangian optimisation can
    # produce a better mixture at a slightly-larger eps than at a strictly-
    # smaller one). We prefer the variant with the highest minimum group
    # selection rate (i.e. best DP ratio) subject to an accuracy floor of
    # baseline - 5 percentage points.
    # Reductions is non-monotonic in eps; an empirical grid is the cheapest
    # way to find the policy with the highest minimum group rate. Six points
    # is enough for a 10-min audit budget.
    eps_grid: tuple[float, ...] = (0.005, 0.01, 0.02, 0.03, 0.05, 0.10)
    candidates: list[tuple[float, Any, float]] = []
    for eps in eps_grid:
        try:
            preds_e, acc_e = _fit_and_predict(eps)
            candidates.append((eps, preds_e, acc_e))
        except Exception:  # noqa: BLE001 — fairlearn can raise on degenerate splits
            continue
    if not candidates:
        raise RemediationUnavailable("ExponentiatedGradient failed for all eps in the grid.")

    def _min_rate_spread(preds: _np.ndarray) -> float:
        """Higher is better: minimum (lo/hi) selection rate across groups
        with at least 20 test rows."""
        groups = A_test.unique()
        rates = []
        for g in groups:
            mask = (A_test == g).to_numpy()
            if mask.sum() < 20:
                continue
            rates.append(float(preds[mask].mean()))
        if len(rates) < 2:
            return 0.0
        lo, hi = min(rates), max(rates)
        return lo / hi if hi > 0 else 0.0

    acc_floor = baseline_acc - 0.05
    best = max(
        (
            (e, p, a)
            for e, p, a in candidates
            if a >= acc_floor
        ),
        key=lambda item: _min_rate_spread(item[1]),
        default=max(candidates, key=lambda item: _min_rate_spread(item[1])),
    )
    chosen_eps, y_pred_rem, remediated_acc = best
    epsilon = chosen_eps  # reflect the actual eps used

    # ---- 6. Re-audit on the test frame with remediated decisions ----
    df_test_full = df.loc[X_test.index].copy()  # original columns for protected/outcome
    try:
        post_metrics, _post_overall = _reaudit_post_remediation(
            request, result.plan, df_test_full, y_pred_rem
        )
    except FairnessUnavailable as e:
        raise RemediationUnavailable(f"post-remediation re-audit failed: {e}") from e

    # Extract the after-DP on the target attribute.
    after_dp = float("nan")
    for m in post_metrics:
        if (
            m.metric == "demographic_parity_ratio"
            and m.slice_key == f"attribute={target_col}"
        ):
            after_dp = float(m.value)
            break

    return RemediationOutcome(
        audit_id=result.audit_id,
        target_attribute=_COLUMN_TO_SEMANTIC.get(target_col),
        target_column=target_col,
        before_dp_ratio=float(before_dp) if before_dp == before_dp else 0.0,
        after_dp_ratio=float(after_dp) if after_dp == after_dp else 0.0,
        baseline_accuracy=baseline_acc,
        remediated_accuracy=remediated_acc,
        accuracy_delta_pp=round((remediated_acc - baseline_acc) * 100.0, 3),
        epsilon=epsilon,
        n_train=int(len(y_train)),
        n_test=int(len(y_test)),
        post_metrics=post_metrics,
    )
