"""End-to-end audit tests for train_baseline=True.

When the user opts in, the audit pipeline should:
1. Train an ephemeral LogisticRegression on non-protected features.
2. Use its predict_proba as the score column.
3. Surface a counterfactual report and a root-cause report.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from nyayai_fairness.audit import run_audit
from nyayai_fairness.schemas import AuditRequest


def _write_parquet(df: pd.DataFrame, tmp_path: Path) -> Path:
    out = tmp_path / "ds.parquet"
    df.to_parquet(out, index=False)
    return out


def test_audit_with_train_baseline_emits_counterfactual_and_root_cause(
    tmp_path: Path,
) -> None:
    rng = np.random.default_rng(0)
    n = 800
    df = pd.DataFrame(
        {
            "caste": rng.choice(["GENERAL", "SC"], size=n, p=[0.6, 0.4]),
            "gender": rng.choice(["FEMALE", "MALE"], size=n),
            "pincode": rng.integers(100_000, 999_999, size=n).astype(float),
            "income": rng.integers(5_000, 80_000, size=n).astype(float),
            "approved": rng.binomial(1, 0.5, size=n),
        }
    )
    path = _write_parquet(df, tmp_path)
    req = AuditRequest(
        dataset_uri=str(path),
        protected_columns=["caste", "gender"],
        outcome_column="approved",
        model_score_column=None,
        train_baseline=True,
        dp_k_anonymity=10,
        min_slice_n=10,
    )
    res = run_audit(req)
    assert res.counterfactual is not None
    assert res.counterfactual.protected_column == "caste"
    assert 0.0 <= res.counterfactual.directional_flip_rate <= 1.0
    assert res.root_cause is not None
    assert res.root_cause.protected_column == "caste"
    assert 0.0 <= res.root_cause.baseline_dp_gap <= 1.0
    # Determinism: same input → same hash.
    assert run_audit(req).determinism_hash == res.determinism_hash


def test_audit_without_train_baseline_omits_extensions(tmp_path: Path) -> None:
    rng = np.random.default_rng(1)
    n = 200
    df = pd.DataFrame(
        {
            "caste": rng.choice(["GENERAL", "SC"], size=n),
            "income": rng.integers(5_000, 50_000, size=n),
            "approved": rng.binomial(1, 0.5, size=n),
            "model_score": rng.random(size=n),
        }
    )
    path = _write_parquet(df, tmp_path)
    req = AuditRequest(
        dataset_uri=str(path),
        protected_columns=["caste"],
        outcome_column="approved",
        model_score_column="model_score",
        train_baseline=False,
        dp_k_anonymity=10,
    )
    res = run_audit(req)
    assert res.counterfactual is None
    assert res.root_cause is None


def test_audit_emits_rbi_metrics_when_loan_amount_present(tmp_path: Path) -> None:
    rng = np.random.default_rng(3)
    n = 600
    df = pd.DataFrame(
        {
            "caste": rng.choice(["GENERAL", "SC", "ST"], size=n, p=[0.85, 0.10, 0.05]),
            "loan_amount": rng.integers(5_000, 50_000, size=n).astype(float),
            "income": rng.integers(5_000, 80_000, size=n).astype(float),
            "approved": rng.binomial(1, 0.7, size=n),
            "model_score": rng.random(size=n),
        }
    )
    path = _write_parquet(df, tmp_path)
    req = AuditRequest(
        dataset_uri=str(path),
        protected_columns=["caste"],
        outcome_column="approved",
        model_score_column="model_score",
        dp_k_anonymity=10,
        min_slice_n=10,
    )
    res = run_audit(req)
    cim = res.custom_india_metrics
    # SC at ~10% should clear the 4.5% target; ST at ~5% might or might not.
    assert cim.rbi_spls is not None
    assert "SC" in cim.rbi_spls["actual_pct_by_group"]
    assert "ST" in cim.rbi_spls["actual_pct_by_group"]
    assert cim.rbi_lrb is not None
    assert "rejection_rate_ratio" in cim.rbi_lrb
    assert cim.rbi_dlf is not None
    assert 0.0 <= cim.rbi_dlf["score"] <= 1.0
