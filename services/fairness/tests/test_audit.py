"""End-to-end audit pipeline tests.

No mocking of Fairlearn --- real computation on synthetic data throughout.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ensure the MUDRA-Lite generator is importable.
_MUDRA_DIR = Path(__file__).resolve().parents[3] / "benchmarks" / "mudra-lite"
sys.path.insert(0, str(_MUDRA_DIR))

from nyayai_fairness.audit import run_audit  # noqa: E402
from nyayai_fairness.schemas import AuditRequest  # noqa: E402


def _write_parquet(df: pd.DataFrame, tmp_path: Path) -> Path:
    out = tmp_path / "ds.parquet"
    df.to_parquet(out, index=False)
    return out


def test_audit_runs_on_tiny_in_memory_frame(tmp_path: Path) -> None:
    rng = np.random.default_rng(0)
    n = 400
    df = pd.DataFrame(
        {
            "gender": rng.choice(["FEMALE", "MALE"], size=n),
            "caste": rng.choice(["GENERAL", "SC"], size=n),
            "habitation": rng.choice(["RURAL", "URBAN"], size=n),
            "income": rng.integers(5_000, 50_000, size=n),
            "approved": rng.binomial(1, 0.5, size=n),
            "model_score": rng.random(size=n),
        }
    )
    path = _write_parquet(df, tmp_path)
    req = AuditRequest(
        dataset_uri=str(path),
        protected_columns=["gender", "caste", "habitation"],
        outcome_column="approved",
        model_score_column="model_score",
        dp_k_anonymity=10,  # low k for a tiny test fixture
    )
    result = run_audit(req)
    assert result.n_rows == n
    # Three per-attribute blocks.
    assert set(result.per_attribute_metrics.keys()) == {"gender", "caste", "habitation"}
    # SPLS should be present.
    assert result.custom_india_metrics.spls is not None
    # Determinism hash should be reproducible.
    result2 = run_audit(req)
    assert result.determinism_hash == result2.determinism_hash


def test_audit_reproduces_mudra_lite_baseline(tmp_path: Path) -> None:
    """MUDRA-Lite seed=42 must trip the 4/5ths rule on caste_disclosed.

    This is the demo-critical baseline from IMPLEMENTATION_PLAN §15:
    pre-remediation DP ratio ~0.55-0.65 (headline 0.61).
    """

    import generate as mudra  # from benchmarks/mudra-lite

    df = mudra.generate(n=10_000, seed=42)
    path = _write_parquet(df, tmp_path)

    req = AuditRequest(
        dataset_uri=str(path),
        protected_columns=["caste_disclosed", "gender", "habitation"],
        outcome_column="approved",
        model_score_column="model_score",
        dp_k_anonymity=200,
        min_slice_n=30,
    )
    result = run_audit(req)
    caste_dp = result.per_attribute_metrics["caste_disclosed"]["demographic_parity_ratio"]
    assert caste_dp < 0.65, f"expected pre-remediation DP ratio < 0.65, got {caste_dp:.3f}"

    # And the warning should be raised.
    assert any("4/5ths" in w for w in result.warnings)

    # Determinism: same request => same hash.
    result2 = run_audit(req)
    assert result.determinism_hash == result2.determinism_hash


def test_audit_rejects_missing_columns(tmp_path: Path) -> None:
    df = pd.DataFrame({"approved": [0, 1, 0, 1]})
    path = _write_parquet(df, tmp_path)
    req = AuditRequest(
        dataset_uri=str(path),
        protected_columns=["gender"],
        outcome_column="approved",
    )
    with pytest.raises(ValueError):
        run_audit(req)


def test_audit_emits_proxy_warning_for_undeclared_proxy(tmp_path: Path) -> None:
    # A column named "jati" that is not declared as protected should warn.
    rng = np.random.default_rng(1)
    n = 200
    df = pd.DataFrame(
        {
            "gender": rng.choice(["FEMALE", "MALE"], size=n),
            "jati": rng.choice(["GENERAL", "SC"], size=n),  # proxies caste
            "approved": rng.binomial(1, 0.5, size=n),
            "model_score": rng.random(size=n),
        }
    )
    path = _write_parquet(df, tmp_path)
    req = AuditRequest(
        dataset_uri=str(path),
        protected_columns=["gender"],  # caste NOT declared
        outcome_column="approved",
        model_score_column="model_score",
        dp_k_anonymity=10,
    )
    result = run_audit(req)
    assert any("jati" in w and "caste" in w for w in result.warnings)
