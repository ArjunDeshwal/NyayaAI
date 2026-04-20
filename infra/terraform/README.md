# infra/terraform — Infrastructure as Code

GCP resources for NyayaAI. Owner subagent: `infra-security-engineer`.

## Layout

```
modules/
  vpc/            VPC Service Controls perimeter
  kms/            CMEK key rings and rotation policy
  iam/            Roles: auditor, reviewer, admin, citizen, ombudsman, support
  firestore/      Operational DB with security rules
  bigquery/       Metrics warehouse (CMEK)
  pubsub/         Event bus topics and subscriptions
  cloud-run/      Services (api, orchestrator, fairness, watcher, reporter)
  vertex/         Agent Engine, Pipelines, Model Registry

envs/
  staging/        Pre-prod, open to team
  prod/           Admin-approval-gated
```

## Hard rules

- asia-south1 (Mumbai) primary. asia-south2 (Delhi) for DR.
- VPC-SC perimeter around every fairness workload.
- CMEK on every bucket and BQ dataset.
- Workload Identity Federation only — no service-account keys.
- Every bucket and dataset has object-retention / table-retention set per `docs/COMPLIANCE.md`.
- `terraform plan` on every PR. `apply` requires manual GitHub environment approval.

## Workflow

```bash
cd infra/terraform/envs/staging
terraform init
terraform plan
terraform apply   # CI only in prod
```

## State

Remote state in a CMEK-encrypted GCS bucket in a separate `nyayai-tfstate` project. Lockfile committed.
