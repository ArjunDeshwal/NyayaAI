"""Dataset ingestion + proxy warning emitter.

Load a parquet / CSV file, validate that the declared protected and outcome
columns exist, and run the India-taxonomy proxy heuristics to emit
warnings (without mutating the data).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from nyayai_taxonomy import ColumnMapper
from nyayai_taxonomy.proxies import detect_surname_caste_proxy, pin_to_district


@dataclass(frozen=True)
class IngestResult:
    df: pd.DataFrame
    warnings: list[str] = field(default_factory=list)
    column_mapping: dict[str, str | None] = field(default_factory=dict)


def load_dataset(uri: str) -> pd.DataFrame:
    """Load a parquet (preferred) or CSV file from a local path.

    For the prototype only local paths are supported; remote URIs are left
    for the finals scope (GCS/S3 via pyarrow FS).
    """

    p = Path(uri)
    if not p.exists():
        raise FileNotFoundError(f"dataset not found: {uri}")
    suffix = p.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(p)
    if suffix in {".csv", ".tsv"}:
        sep = "," if suffix == ".csv" else "\t"
        return pd.read_csv(p, sep=sep)
    raise ValueError(f"unsupported dataset format: {suffix}")


def ingest(
    uri: str,
    *,
    protected_columns: list[str],
    outcome_column: str,
    model_score_column: str | None = None,
) -> IngestResult:
    """Load ``uri`` and validate schema; emit proxy / taxonomy warnings."""

    df = load_dataset(uri)
    warnings: list[str] = []

    required = [*protected_columns, outcome_column]
    if model_score_column is not None:
        required.append(model_score_column)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns in dataset: {missing}")

    mapper = ColumnMapper()
    column_mapping: dict[str, str | None] = {}
    for col in df.columns:
        hit = mapper.map_column(col)
        column_mapping[col] = hit.canonical_attr

    # Warn on *non-declared* columns that map to protected attributes: likely
    # a proxy leaking into the feature set.
    declared = set(protected_columns)
    for col, mapped in column_mapping.items():
        if mapped is not None and col not in declared and col not in {outcome_column, model_score_column}:
            warnings.append(
                f"column '{col}' maps to protected attribute '{mapped}' but was not "
                "declared as protected; it will be treated as a feature and may leak"
            )

    # Surname column heuristic: if a column looks like a surname, run the
    # surname-caste proxy detector on a sample.
    surname_candidates = [
        c for c in df.columns if c.lower() in {"surname", "last_name", "family_name"}
    ]
    for col in surname_candidates:
        sample = df[col].dropna().astype(str).head(200)
        if sample.empty:
            continue
        mean_leak = float(sample.map(detect_surname_caste_proxy).mean())
        if mean_leak >= 0.3:
            warnings.append(
                f"column '{col}' has mean surname-caste proxy score {mean_leak:.2f}; "
                "treat as a caste proxy and consider dropping from features"
            )

    # PIN heuristic
    pin_candidates = [c for c in df.columns if c.lower() in {"pin", "pincode", "pin_code", "zip"}]
    for col in pin_candidates:
        sample = df[col].dropna().astype(str).head(200)
        if sample.empty:
            continue
        mapped = sample.map(pin_to_district)
        if mapped.notna().mean() >= 0.5:
            warnings.append(
                f"column '{col}' looks like an Indian PIN code; PIN proxies caste at "
                "sub-district level (IFF-Vidhi 2021) --- will emit district-level warning"
            )

    return IngestResult(df=df, warnings=warnings, column_mapping=column_mapping)
