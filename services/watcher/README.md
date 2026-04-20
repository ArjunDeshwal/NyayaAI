# services/watcher — Continuous Fairness Drift Monitor

Post-deploy continuous monitoring. Polls production model endpoints on user-configured frequency, runs a lightweight fairness probe, and alerts (Pub/Sub → email/Slack) on drift beyond threshold.

Owner: `infra-security-engineer` (infra), `agent-architect` (Gemini 3 Flash prompt).

## Why Go?

Watcher is a scheduled, long-lived polling loop. Go's goroutines + smaller runtime footprint + faster cold-start on Cloud Run make it the right choice over Python for this one service.

## Stack

- Go 1.23
- Cloud Run (scheduled via Cloud Scheduler + Pub/Sub)
- Firestore (time-series) · BigQuery (aggregates)
- Gemini 3 Flash (via `google.golang.org/genai`)
- Breach-notifier microservice: drafts DPDP Rule 12 72-hour notifications.

## Run

```bash
go mod download
go run ./cmd/watcher
go test ./...
```
