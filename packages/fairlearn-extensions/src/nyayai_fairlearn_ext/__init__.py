"""NyayaAI custom fairness-metric extensions.

This layer is *deliberately classical* --- no LLM calls. It complements
Fairlearn 0.12+ with India-context metrics that Fairlearn does not ship:

- :func:`metrics.spls.surname_proxy_leakage_score` --- SPLS
- :func:`metrics.lrb.linguistic_register_bias` --- LRB
- :func:`metrics.dlf.digital_literacy_fairness` --- DLF

It also wraps Fairlearn's standard group-fairness metrics (DP, EO, EOpp,
FPR diff) in :mod:`wrappers` so callers get a stable return-shape.
"""

from nyayai_fairlearn_ext.counterfactual import (
    CounterfactualExample,
    CounterfactualResult,
    compute_counterfactual_flips,
)
from nyayai_fairlearn_ext.metrics.dlf import DLFResult, digital_literacy_fairness
from nyayai_fairlearn_ext.metrics.lrb import LRBResult, linguistic_register_bias
from nyayai_fairlearn_ext.metrics.spls import SPLSResult, surname_proxy_leakage_score
from nyayai_fairlearn_ext.root_cause import (
    FeatureContribution,
    RootCauseResult,
    compute_root_cause,
)
from nyayai_fairlearn_ext.wrappers import (
    GroupFairnessResult,
    IntersectionalResult,
    compute_group_fairness,
    compute_intersectional_fairness,
)

__all__ = [
    "CounterfactualExample",
    "CounterfactualResult",
    "DLFResult",
    "FeatureContribution",
    "GroupFairnessResult",
    "IntersectionalResult",
    "LRBResult",
    "RootCauseResult",
    "SPLSResult",
    "compute_counterfactual_flips",
    "compute_group_fairness",
    "compute_intersectional_fairness",
    "compute_root_cause",
    "digital_literacy_fairness",
    "linguistic_register_bias",
    "surname_proxy_leakage_score",
]
