# IMPACT — Quantified Theory of Change

Owner: `product-research-lead`.

## Problem in numbers

- **15.1 million** people lost PDS access under Aadhaar-seeded targeting (Muralidharan et al., NBER w26744, 2020; ~10pp exclusion).
- **1.86 million** ration cards cancelled in Telangana by the Samagra Vedika algorithm with no individual appeal (Amnesty, 2024).
- **Santoshi Kumari**, 11, died of starvation in Simdega, Jharkhand, after her family's ration card was de-linked (Sept 2017).
- **200 million** patients affected by the US commercial-risk algorithm that reduced Black enrolment; corrected model raised it 17.7% → 46.5% (Obermeyer et al., *Science* 2019).
- **26,000** Dutch families wrongfully accused in the toeslagenaffaire.

## Theory of change

**Activities** (audits) → **Outputs** (findable, explainable bias + remediation playbook + DPIA) → **Outcomes** (institution fixes or halts the model; citizen gets evidence for grievance) → **Impact** (reduction in wrongful exclusion).

## Year-1 targets

| Indicator | Baseline | Target (12 months) | Source |
|---|---|---|---|
| Audits completed | 0 | 25 | Product telemetry |
| Government/CSO partners | 0 | 5 | Signed MoUs |
| Remediated models | 0 | 10 | Follow-up audit diff |
| Citizen complaints generated | 0 | 1,000 | Grievance portal exports |
| Media / research citations | 0 | 20 | Google Scholar + news |

## Demo impact (MUDRA-Lite, simulated)

| Metric | Before | After | Note |
|---|---|---|---|
| Demographic Parity ratio | 0.61 | 0.94 | +54% |
| Equalised Odds difference | 0.21 | 0.04 | −81% |
| Accuracy | 0.803 | 0.799 | −0.4pp (negligible) |
| Caste-surname leakage (SPLS) | 0.78 | 0.52 | near chance |

## Long-term

NyayaAI aspires to be the open, India-first equivalent of what SOC-2 is for security: a *must-show* artifact before any public-interest model is deployed.
