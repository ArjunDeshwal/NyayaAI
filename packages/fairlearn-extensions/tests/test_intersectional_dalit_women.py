"""Targeted intersectional-fairness test: Dalit women.

Verifies that ``compute_intersectional_fairness`` surfaces the
``(SC, FEMALE)`` cell as distinctly worse than either the ``SC`` marginal
or the ``FEMALE`` marginal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from nyayai_fairlearn_ext import compute_group_fairness, compute_intersectional_fairness


def test_dalit_women_intersection_is_worse_than_marginals() -> None:
    rng = np.random.default_rng(7)
    n = 1200
    caste = rng.choice(["GENERAL", "SC"], size=n, p=[0.7, 0.3])
    gender = rng.choice(["MALE", "FEMALE"], size=n, p=[0.5, 0.5])

    # Selection rates (post-thresholded model decisions):
    #   GENERAL × MALE   : 0.85
    #   GENERAL × FEMALE : 0.70
    #   SC      × MALE   : 0.55
    #   SC      × FEMALE : 0.10  (the intersectional smoking gun)
    p_pos = np.full(n, 0.0)
    p_pos[(caste == "GENERAL") & (gender == "MALE")] = 0.85
    p_pos[(caste == "GENERAL") & (gender == "FEMALE")] = 0.70
    p_pos[(caste == "SC") & (gender == "MALE")] = 0.55
    p_pos[(caste == "SC") & (gender == "FEMALE")] = 0.10
    y_pred = (rng.random(size=n) < p_pos).astype(int)
    y_true = rng.binomial(1, 0.5, size=n)

    # Marginals
    marginal_caste = compute_group_fairness(y_true, y_pred, pd.Series(caste))
    marginal_gender = compute_group_fairness(y_true, y_pred, pd.Series(gender))

    # Intersectional
    df = pd.DataFrame({"caste": caste, "gender": gender})
    inter = compute_intersectional_fairness(y_true, y_pred, df)

    # Dalit-women cell selection rate is well below each marginal's worst.
    sc_female_rate = inter.metrics_by_slice[("SC", "FEMALE")]["selection_rate"]
    assert sc_female_rate < 0.20

    # Worst per-attribute rate is much higher than the intersection.
    sc_rate = marginal_caste.selection_rate_by_group["SC"]
    female_rate = marginal_gender.selection_rate_by_group["FEMALE"]
    assert sc_female_rate < sc_rate - 0.10
    assert sc_female_rate < female_rate - 0.10
