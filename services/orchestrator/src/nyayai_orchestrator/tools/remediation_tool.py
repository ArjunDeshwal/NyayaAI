"""Classical remediation tool.

Deterministic, non-LLM. Takes the original :class:`AuditRequest` plus the
already-computed :class:`AuditResult`, selects a protected attribute whose
*shape* (group cardinality, smallest-group size) actually admits
reductions-style mitigation, retrains under a Fairlearn
:class:`~fairlearn.reductions.ExponentiatedGradient` /
:class:`~fairlearn.reductions.DemographicParity` constraint, re-runs the
classical fairness audit on the remediated predictions, and enforces a
keep-or-discard gate before returning.

Why shape filtering is load-bearing
-----------------------------------
``ExponentiatedGradient + DemographicParity`` is *reductions with Lagrangian
reweighting*. With 20+ groups and some groups holding n<30, the constraint
set becomes nearly singular and the solver picks a policy that trades
accuracy for parity that is worse than the unconstrained baseline (observed
in production: 5-attribute MUDRA-Lite run, state was picked as target,
DP went from 0.608 to 0.342, accuracy dropped 1.33 pp). The fix is to
(a) refuse to pick such attributes, and (b) gate the output so a degraded
run never ships.

Why LLM?
--------
This module has *none*. The math is classical; an LLM would only introduce
non-determinism into a keep-or-discard gate. Gemini reappears downstream in
the Remediation narrator agent, which restates the numbers this tool
produces — it is contractually forbidden from inventing them.

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


# ---- Keep-or-discard gate thresholds ---------------------------------------
# DP must improve by at least 5 percentage points of the ratio, AND accuracy
# must not drop by more than 3 percentage points. Both are required — a tiny
# DP lift paid for by a large accuracy loss is not a good trade.
_DP_MIN_LIFT = 0.05
_ACC_MIN_DELTA_PP = -3.0

# ---- Target-shape rules ----------------------------------------------------
# Reductions breaks down empirically above ~10 groups and with tiny groups.
_MAX_TARGET_GROUPS = 10
_MIN_SMALLEST_GROUP = 50

# ---- Wider eps sweep -------------------------------------------------------
# Reductions under DP is non-monotonic in eps; an empirical grid is the
# cheapest way to find the policy with the highest minimum group rate.
# Expanded from the original 6-point grid to 9 points so the sweep can find a
# larger-eps policy that the tight end couldn't reach on awkward datasets.
_EPS_GRID: tuple[float, ...] = (
    0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.25,
)


class RemediationUnavailable(RuntimeError):
    """Raised when Fairlearn / sklearn is missing, or the input is malformed.

    Callers (the orchestrator) catch this and skip the remediation step
    cleanly instead of failing the whole audit.
    """


class RemediationOutcome(BaseModel):
    """Structured output of the classical remediation pass.

    This is what the LLM narrative agent receives — it never invents these
    numbers, it only restates them.

    When ``improved`` is False, the classical gate rejected the remediated
    policy (either no tractable target existed, or the sweep did not find a
    policy meeting the DP-lift / accuracy-floor requirements). In that case
    ``after_dp_ratio`` equals ``before_dp_ratio`` and ``risks`` contains a
    plain-English reason.
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
    # True iff the gate accepted this run. When False, the orchestrator /
    # narrator must surface "no improvement" rather than claim one.
    improved: bool = False
    # Group cardinality the tool saw on the chosen target column. None when
    # no target was selected.
    target_group_count: int | None = Field(default=None, ge=0)
    # Short, truthful reason when ``improved`` is False. Empty string on
    # accepted runs. Surfaced in ``risks`` by the narrator.
    reason: str = ""
    # Optional re-audit metric rows; handy for logs / PDFs.
    post_metrics: list[SliceMetric] = Field(default_factory=list)


@dataclass(frozen=True)
class _AttrCandidate:
    """Candidate protected attribute, annotated with shape information."""

    column: str
    dp_ratio: float
    n_groups: int
    smallest_group_n: int


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


def _per_attribute_dp(result: AuditResult) -> dict[str, float]:
    """Map ``column_name -> demographic_parity_ratio`` from the audit result."""
    out: dict[str, float] = {}
    for m in result.metrics:
        if m.metric != "demographic_parity_ratio":
            continue
        if not m.slice_key.startswith("attribute="):
            continue
        attr = m.slice_key.removeprefix("attribute=")
        val = float(m.value)
        if val != val:  # NaN check
            continue
        # Take the first non-NaN we see per attribute (there should only be one).
        out.setdefault(attr, val)
    return out


def _rank_candidates(
    candidates: list[_AttrCandidate],
) -> _AttrCandidate | None:
    """Pick the tractable-shape candidate with the worst DP ratio.

    An attribute is *tractable* if it has at most :data:`_MAX_TARGET_GROUPS`
    groups AND the smallest group has at least :data:`_MIN_SMALLEST_GROUP`
    rows. Among the tractable candidates we prefer the worst (lowest) DP
    ratio — that's the attribute most in need of mitigation.
    """
    tractable = [
        c
        for c in candidates
        if c.n_groups <= _MAX_TARGET_GROUPS
        and c.smallest_group_n >= _MIN_SMALLEST_GROUP
    ]
    if not tractable:
        return None
    return min(tractable, key=lambda c: c.dp_ratio)


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
    """Call the classical fairness engine on the remediated predictions."""
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


def _skipped_outcome(
    *,
    audit_id: str,
    target_column: str,
    target_attribute: ProtectedAttribute | None,
    before_dp_ratio: float,
    target_group_count: int | None,
    reason: str,
) -> RemediationOutcome:
    """Build a ``not-improved`` outcome that keeps the original model."""
    # before_dp_ratio may be NaN (no DP metric was available); clamp to 0.0
    # for the contract, but remember the true value by setting after = before.
    safe_before = before_dp_ratio if before_dp_ratio == before_dp_ratio else 0.0
    safe_before = max(0.0, min(1.0, float(safe_before)))
    return RemediationOutcome(
        audit_id=audit_id,
        target_attribute=target_attribute,
        target_column=target_column,
        before_dp_ratio=safe_before,
        after_dp_ratio=safe_before,  # original model retained
        baseline_accuracy=0.0,
        remediated_accuracy=0.0,
        accuracy_delta_pp=0.0,
        epsilon=0.0,
        n_train=0,
        n_test=0,
        improved=False,
        target_group_count=target_group_count,
        reason=reason,
        post_metrics=[],
    )


def run_remediation(
    request: AuditRequest,
    result: AuditResult,
    *,
    epsilon: float = 0.05,  # retained for back-compat; sweep is authoritative
    test_fraction: float = 0.3,
    random_state: int = 42,
) -> RemediationOutcome:
    """Retrain under Demographic Parity and re-audit, with a gate.

    Strategy (deterministic):
      1. Compute per-attribute DP ratios and group-shape annotations from
         the dataset.
      2. Among attributes with at most ``_MAX_TARGET_GROUPS`` groups AND
         smallest-group n at least ``_MIN_SMALLEST_GROUP``, pick the one
         with the worst DP ratio. If none is tractable, return a not-
         improved outcome with a truthful reason.
      3. 70/30 stratified train/test split, seed = ``random_state``.
      4. Baseline estimator: LogisticRegression (or GradientBoostingClassifier
         when the target attribute's group count exceeds 10 — trees handle
         high-cardinality conditional distributions better; unused on
         tractable targets today but wired so the path exists).
      5. Remediated = ``ExponentiatedGradient(..., DemographicParity(eps))``
         over the expanded 9-point eps grid. We select the policy with the
         highest ``after_dp_ratio`` (from the re-audit) subject to an
         accuracy floor.
      6. Keep-or-discard gate: accept only if
         ``after_dp_ratio >= before_dp_ratio + 0.05`` AND
         ``accuracy_delta_pp >= -3.0``. Otherwise return the not-improved
         outcome and let the narrator say so.
    """
    # ---- Lazy imports ------------------------------------------------------
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

    # ---- Load dataset (needed up-front for group-shape ranking) ------------
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

    if ds.outcome_column not in df.columns:
        raise RemediationUnavailable(
            f"outcome column '{ds.outcome_column}' missing from dataset."
        )

    # ---- 1+2. Rank candidate attributes by tractable shape × worst DP ------
    dp_by_attr = _per_attribute_dp(result)
    candidates: list[_AttrCandidate] = []
    for col in ds.candidate_protected_columns:
        if col not in df.columns:
            continue
        vc = df[col].astype(str).value_counts()
        n_groups = int(len(vc))
        smallest = int(vc.min()) if n_groups > 0 else 0
        # Missing DP — use NaN so the candidate is still scored for shape
        # but ranked last (only non-NaN DP is considered by the ranker).
        dp_val = dp_by_attr.get(col)
        if dp_val is None or dp_val != dp_val:
            # We still need *some* number for ranking; use 1.0 so the
            # candidate only wins if nothing else has a DP ratio.
            dp_val = 1.0
        candidates.append(
            _AttrCandidate(
                column=col,
                dp_ratio=float(dp_val),
                n_groups=n_groups,
                smallest_group_n=smallest,
            )
        )

    chosen = _rank_candidates(candidates)
    if chosen is None:
        # No attribute meets the shape rule. Record the best-available
        # before-DP so the report carries a truthful number, and skip.
        worst_any = min(
            (c for c in candidates),
            key=lambda c: c.dp_ratio,
            default=None,
        )
        before_dp_for_record = (
            worst_any.dp_ratio if worst_any is not None else float("nan")
        )
        target_col_record = (
            worst_any.column if worst_any is not None
            else (ds.candidate_protected_columns[0] if ds.candidate_protected_columns else "")
        )
        target_group_count = worst_any.n_groups if worst_any is not None else None
        return _skipped_outcome(
            audit_id=result.audit_id,
            target_column=target_col_record,
            target_attribute=_COLUMN_TO_SEMANTIC.get(target_col_record),
            before_dp_ratio=before_dp_for_record,
            target_group_count=target_group_count,
            reason=(
                "no target with tractable cardinality; remediation skipped "
                f"(required: <= {_MAX_TARGET_GROUPS} groups and smallest "
                f"group n >= {_MIN_SMALLEST_GROUP})"
            ),
        )

    target_col = chosen.column
    before_dp = chosen.dp_ratio
    target_group_count = chosen.n_groups

    # ---- 3. Prepare features + sensitive feature ---------------------------
    y = df[ds.outcome_column].astype(int).to_numpy()
    A = df[target_col].astype(str)  # sensitive feature (str for ExpGrad)

    exclude = {
        ds.outcome_column,
        *ds.candidate_protected_columns,
    }
    if ds.model_score_column:
        exclude.add(ds.model_score_column)
    for c in list(df.columns):
        if c.lower() in {"applicant_id", "id"}:
            exclude.add(c)

    X = _coerce_feature_frame(df, exclude=exclude)

    # Stratify by (group × label) so both sides see every cell.
    strat = A.astype(str) + "__" + pd.Series(y, index=A.index).astype(str)
    try:
        X_train, X_test, y_train, y_test, A_train, A_test = train_test_split(
            X, y, A, test_size=test_fraction, random_state=random_state, stratify=strat
        )
    except ValueError:
        X_train, X_test, y_train, y_test, A_train, A_test = train_test_split(
            X, y, A, test_size=test_fraction, random_state=random_state
        )

    # ---- 4. Base estimator factory -----------------------------------------
    # For tractable targets (<=10 groups), LogisticRegression is enough.
    # For high-cardinality targets we would use GradientBoostingClassifier —
    # this branch is guarded above, but we keep the factory so that future
    # callers that pass their own shape constraints can exercise the path.
    def _make_base_estimator() -> Any:
        if target_group_count is not None and target_group_count > 10:
            from sklearn.ensemble import (  # lazy — heavier import
                GradientBoostingClassifier,
            )
            return GradientBoostingClassifier(
                n_estimators=50,
                max_depth=3,
                random_state=random_state,
            )
        return LogisticRegression(max_iter=1000, solver="liblinear")

    baseline = _make_base_estimator()
    baseline.fit(X_train, y_train)
    y_pred_base = baseline.predict(X_test)
    baseline_acc = float(accuracy_score(y_test, y_pred_base))

    # ---- 5. Remediated model (eps sweep) -----------------------------------
    # ExponentiatedGradient returns a *randomized* classifier — calling
    # ``.predict`` samples from the mixture, which makes the numbers bounce.
    # We threshold the deterministic PMF (Agarwal et al. 2018 §4) for
    # reproducibility.
    import numpy as _np

    def _fit_and_predict(eps: float) -> tuple["Any", float]:
        constraint = DemographicParity(difference_bound=eps)
        mit = ExponentiatedGradient(
            estimator=_make_base_estimator(),
            constraints=constraint,
            eps=eps,
        )
        mit.fit(X_train, y_train, sensitive_features=A_train)
        probs = mit._pmf_predict(X_test)[:, 1]
        preds = (probs >= 0.5).astype(int)
        acc = float(accuracy_score(y_test, preds))
        return preds, acc

    candidates_sweep: list[tuple[float, Any, float]] = []
    for eps in _EPS_GRID:
        try:
            preds_e, acc_e = _fit_and_predict(eps)
            candidates_sweep.append((eps, preds_e, acc_e))
        except Exception:  # noqa: BLE001 — fairlearn can raise on degenerate splits
            continue
    if not candidates_sweep:
        return _skipped_outcome(
            audit_id=result.audit_id,
            target_column=target_col,
            target_attribute=_COLUMN_TO_SEMANTIC.get(target_col),
            before_dp_ratio=before_dp,
            target_group_count=target_group_count,
            reason=(
                "ExponentiatedGradient failed for every epsilon in the sweep; "
                "original model retained."
            ),
        )

    # Score each candidate by its empirical min/max group selection-rate
    # ratio on the test frame — a cheap proxy for the eventual re-audit DP
    # ratio. We then re-audit the winner (expensive) to get the authoritative
    # post-DP number.
    def _min_rate_spread(preds: _np.ndarray) -> float:
        groups = A_test.unique()
        rates: list[float] = []
        for g in groups:
            mask = (A_test == g).to_numpy()
            if mask.sum() < 20:
                continue
            rates.append(float(preds[mask].mean()))
        if len(rates) < 2:
            return 0.0
        lo, hi = min(rates), max(rates)
        return lo / hi if hi > 0 else 0.0

    # Accuracy floor: don't consider a sweep point that blows past the
    # gate's accuracy threshold. We still keep the candidate as a fallback.
    acc_floor = baseline_acc + (_ACC_MIN_DELTA_PP / 100.0)
    best = max(
        (
            (e, p, a)
            for e, p, a in candidates_sweep
            if a >= acc_floor
        ),
        key=lambda item: _min_rate_spread(item[1]),
        default=max(candidates_sweep, key=lambda item: _min_rate_spread(item[1])),
    )
    chosen_eps, y_pred_rem, remediated_acc = best

    # ---- 6. Re-audit on the test frame with remediated decisions ----------
    df_test_full = df.loc[X_test.index].copy()
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

    # ---- Gate --------------------------------------------------------------
    acc_delta_pp = round((remediated_acc - baseline_acc) * 100.0, 3)
    before_clean = before_dp if before_dp == before_dp else 0.0
    after_clean = after_dp if after_dp == after_dp else 0.0

    dp_ok = after_clean >= (before_clean + _DP_MIN_LIFT)
    acc_ok = acc_delta_pp >= _ACC_MIN_DELTA_PP
    improved = bool(dp_ok and acc_ok)

    if not improved:
        # Original model retained; return a truthful skip.
        return RemediationOutcome(
            audit_id=result.audit_id,
            target_attribute=_COLUMN_TO_SEMANTIC.get(target_col),
            target_column=target_col,
            before_dp_ratio=max(0.0, min(1.0, float(before_clean))),
            # Mirror before so downstream reports don't show a false lift.
            after_dp_ratio=max(0.0, min(1.0, float(before_clean))),
            baseline_accuracy=baseline_acc,
            remediated_accuracy=baseline_acc,  # original model retained
            accuracy_delta_pp=0.0,
            epsilon=chosen_eps,
            n_train=int(len(y_train)),
            n_test=int(len(y_test)),
            improved=False,
            target_group_count=target_group_count,
            reason=(
                "epsilon sweep did not find a policy that improves DP without "
                "degrading accuracy; original model retained. "
                f"(best sweep point: after_dp_ratio={after_clean:.3f}, "
                f"before={before_clean:.3f}, accuracy_delta={acc_delta_pp:+.2f}pp; "
                f"required lift >= +{_DP_MIN_LIFT:.2f} and accuracy_delta >= "
                f"{_ACC_MIN_DELTA_PP:+.1f}pp)"
            ),
            post_metrics=post_metrics,
        )

    return RemediationOutcome(
        audit_id=result.audit_id,
        target_attribute=_COLUMN_TO_SEMANTIC.get(target_col),
        target_column=target_col,
        before_dp_ratio=max(0.0, min(1.0, float(before_clean))),
        after_dp_ratio=max(0.0, min(1.0, float(after_clean))),
        baseline_accuracy=baseline_acc,
        remediated_accuracy=remediated_acc,
        accuracy_delta_pp=acc_delta_pp,
        epsilon=chosen_eps,
        n_train=int(len(y_train)),
        n_test=int(len(y_test)),
        improved=True,
        target_group_count=target_group_count,
        reason="",
        post_metrics=post_metrics,
    )
