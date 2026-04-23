"""Differential-privacy helpers for subgroup metrics.

**Scope (prototype):** we ship a minimal Laplace-noise wrapper and a
k-anonymity-based suppression gate. Finals scope will integrate Google's
``dp_accounting`` library for a composed epsilon/delta budget across all
slices.

Epsilon/delta choices (prototype defaults):

- ``epsilon = 1.0`` per slice-metric query --- tight enough to be a
  meaningful privacy budget, loose enough to preserve signal.
- Sensitivity for a rate metric (selection rate, TPR, FPR) on a slice of
  size ``n`` is ``1/n``. The Laplace noise scale is therefore
  ``1 / (n * epsilon)``.
- Slices with ``n < k_threshold`` are *suppressed* (not published at all):
  noise alone is insufficient when the slice is smaller than the k-anonymity
  threshold.

References:
- Dwork & Roth, *The Algorithmic Foundations of Differential Privacy* (2014),
  Ch. 3 --- the Laplace mechanism.
- Google DP library README --- aligns with the prototype API we plan to
  adopt in the finals scope.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DPConfig:
    epsilon: float = 1.0
    delta: float = 0.0
    k_anonymity: int = 100
    seed: int = 0


def laplace_noise_for_rate(n: int, epsilon: float, rng: np.random.Generator) -> float:
    """Sample Laplace noise with scale ``1 / (n * epsilon)``.

    For a bounded rate metric the ℓ1 sensitivity is ``1/n`` (adding or
    removing one row changes the rate by at most ``1/n``).
    """

    if n <= 0 or epsilon <= 0:
        return 0.0
    scale = 1.0 / (float(n) * float(epsilon))
    return float(rng.laplace(loc=0.0, scale=scale))


def protect_rate(
    value: float,
    n: int,
    config: DPConfig,
    rng: np.random.Generator,
) -> tuple[float, bool]:
    """Return ``(protected_value, was_suppressed)``.

    - If ``n < config.k_anonymity`` the slice is suppressed: we return
      ``(float('nan'), True)``.
    - Otherwise we add Laplace noise and clip to ``[0, 1]``.
    """

    if n < config.k_anonymity:
        return float("nan"), True
    noise = laplace_noise_for_rate(n, config.epsilon, rng)
    noisy = float(np.clip(value + noise, 0.0, 1.0))
    return noisy, False
