# Momentum — Cloud Implementation on AWS

**Status:** Proposed (v1)
**Date:** 2026-08-22
**Owner:** Platform Engineering
**Platform:** Amazon Web Services (ECS Fargate + Terraform)
**Posture:** Staging-first, then production hardening

> This document is the single source of truth for migrating the Momentum platform from
> Render (free tier) to a secure, scalable, highly available AWS deployment. It covers the
> codebase assessment, the target architecture, infrastructure-as-code, CI/CD, observability,
> runbooks, and a phased rollout — end to end.

---

## Table of Contents

1. [Context & Goals](#1-context--goals)
2. [Phase 1 — Codebase Assessment](#2-phase-1--codebase-assessment)
3. [Phase 2 — Target AWS Architecture](#3-phase-2--target-aws-architecture)
4. [Phase 0 — Code Preconditions](#4-phase-0--code-preconditions)
5. [Infrastructure as Code (Terraform)](#5-infrastructure-as-code-terraform)
6. [Network & Security Architecture](#6-network--security-architecture)
7. [Data & State Management](#7-data--state-management)
8. [CI/CD & Deployment Pipeline](#8-cicd--deployment-pipeline)
9. [Observability & Monitoring](#9-observability--monitoring)
10. [Environments & Cost Posture](#10-environments--cost-posture)
11. [Rollout Plan](#11-rollout-plan)
12. [Runbooks](#12-runbooks)
13. [Risks & Mitigations](#13-risks--mitigations)
14. [Appendix — Supporting Details](#14-appendix--supporting-details)

---

## 1. Context & Goals

Momentum is a primary-school assessment platform with an AI-driven oral assessment ("Buddy"),
an 11-step automated report-generation pipeline, a teacher/admin dashboard, and a human
review workflow. It currently runs on Render free tier with several production fragility
points (in-process background fallback, task-local file storage, migrations on boot).

### 1.1 Goals

| Goal | Why |
|---|---|
| Production-grade availability | Zero downtime deploys; surviving AZ/instance failures |
| Durable async pipeline | Interview → report generation must not lose work or double-run |
| Secure by default | Least-privilege IAM, private network, encrypted data at rest and in transit |
| Shared, durable media storage | Replace task-local `static/` disk (lost on restart, not shared) |
| Reproducible infrastructure | Terraform for everything; environments from one codebase |
| Observable | Logs, metrics, alarms, and tracing from day one |
| Cost-aware | Dev/staging lean; production HA only where it matters |

### 1.2 Decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Compute | **ECS Fargate** | Serverless containers; no cluster mgmt; native Blue/Green via CodeDeploy |
| IaC | **Terraform** | Cloud-agnostic, huge ecosystem, state in S3 + DynamoDB locking |
| Order | **Staging first** | Validate multi-instance & storage changes before production spend |
| Async engine | **Celery + ElastiCache Redis** | Zero code churn; replaces the fragile `BackgroundTasks` fallback |

---

## 2. Phase 1 — Codebase Assessment

### 2.1 Repository Layout

```
momentum/
├── primary-assessment/            # Next.js frontend (deployable #1)
│   ├── Dockerfile                 # multi-stage: node:20 build → node:18 runtime
│   ├── next.config.ts
│   └── src/                       # App Router, services, components
└── primary-assessment-backend/    # FastAPI backend + Celery worker (deployable #2)
    ├── Dockerfile                 # python:3.10-slim → uvicorn on :5000
    ├── requirements.txt
    ├── app/
    │   ├── main.py                # app bootstrap + inline migrations + seeds
    │   ├── api/                   # REST routers
    │   ├── ai_assessment/         # report generator, interview engine, audio
    │   ├── services/              # interview_service, evaluation_pipeline, ...
    │   ├── tasks/                 # Celery tasks
    │   ├── infrastructure/        # s3, sendgrid, ai_providers, celery
    │   └── common/ core/          # config, db, models, security
    ├── alembic/                   # present but NOT the migration source of truth
    ├── scripts/                   # setup_db.sh, sync_db_from_render.sh
    └── tests/                     # pytest suite
```

### 2.2 Tech Stack & Dependencies

| Layer | Stack | Runtime |
|---|---|---|
| Frontend | Next.js 16.2.6 (App Router), React 19.2.4, TypeScript, Tailwind, Axios, lucide-react | Node 20 build → Node 18 runtime |
| Backend | FastAPI, Uvicorn, SQLAlchemy 2.0, Pydantic v2 | Python 3.10 |
| Migrations | Alembic (installed, underused) | — |
| Task queue | Celery 5.3 + Redis 7 | broker + result backend |
| Database | PostgreSQL 15 (prod) / SQLite (dev/test) | SQLAlchemy pool 50/+10, `pool_pre_ping` |
| LLM providers | Groq (`llama-3.3-70b-versatile`) → OpenAI (`gpt-4o-mini`) → Gemini (`gemini-2.0-flash`) → local heuristic | `generator.py:_call_llm_with_fallback` |
| Voice | Local Whisper STT + Kokoro TTS — **deprecated/stubbed**; STT/TTS in-browser | — |
| Email | SendGrid v3 REST via urllib | `infrastructure/sendgrid.py` |
| Object storage | AWS S3 via boto3, gated by `PAUSE_S3=true` → local `static/` | `infrastructure/s3.py` |
| PDF ingestion | pypdf; fetch from `ncert.nic.in` (15s timeout) | `utils/ncert_sync.py` |
| Auth | Stateless JWT (7-day expiry), Bearer token in localStorage + cookie for middleware RBAC | `core/security.py` |

### 2.3 Architecture Pattern

**Monolith with a decoupled frontend.** Layered Routes → Services → Repositories →
Models/Schemas, with a legacy `app/core/` mirror and `app/*` redirect shims.

**Entry points:**

| Process | Port | Purpose |
|---|---|---|
| Next.js | 3000 | Admin dashboard, student assessment/result pages |
| FastAPI | 5000 | REST `/api/*`, WebSocket (live interview), `/voice/*`, `/static` mount |
| Celery worker | — | `evaluate_interview_task`, `sync_ncert_chapter_task`, `cleanup_expired_audio_task` |
| Startup side-effects | — | `create_all` + ~40 inline `ALTER TABLE`s + admin seed + NCERT seed on every boot |

**Key flow (async report generation):**

```
Interview completes
   └─ POST /interviews/submit ──► 202 Accepted (return immediately)
         ├─ Redis alive?  ──►  Celery: evaluate_interview_task.delay(interview.id)
         └─ Redis down?   ──►  FastAPI BackgroundTasks fallback  ⚠️ unsafe at scale
Frontend polls GET /interviews/{id}
   status: Evaluation Running → Generating Insights → Report Ready
```

The 11-step pipeline (`EvaluationPipelineService.run_pipeline`) persists per-step status to
`interview_evaluation_steps` and calls LLMs in a Groq→OpenAI→Gemini fallback chain.

### 2.4 State & Storage Demands

| Store | Contents |
|---|---|
| PostgreSQL | `schools, admins, classes, subjects, chapters, questions, assessments, reports, students, student_assessments, interviews, interview_messages, interview_evaluation_steps, conversation_turns, books, book_chapters` |
| Redis | Celery broker + result backend |
| S3 / local `static/` | Student pictures (`picture_url`), interview audio (`static/interviews/{id}/q{n}.wav`), TTS cache, textbook PDFs |
| Ephemeral | `static/` and `cache/` are **task-local disk** — lost on restart, not shared |
| Env/secrets | `SECRET_KEY`, `DATABASE_URL`, `GROQ/OPENAI/GEMINI_API_KEY`, `SENDGRID_*`, `AWS_*`, `CELERY_*`, `FASTER_WHISPER_*`, `KOKORO_BASE_URL`, `FRONTEND_URL` |

### 2.5 External Integrations

| Direction | Integration |
|---|---|
| Outbound | Groq API, OpenAI API, Gemini (Google GenAI), SendGrid API, AWS S3 (boto3), `ncert.nic.in` PDFs |
| Scheduled | None functional — `cleanup_expired_audio_task` exists but no Celery beat schedule is defined |
| Inbound webhooks | None |

### 2.6 Production Blockers Found (must fix in Phase 0)

1. **Inline `ALTER TABLE` migrations on every boot** (`main.py:9-249`) — slow, fragile on RDS; Alembic should be the single migration path.
2. **Task-local disk media** — `save_uploaded_audio` writes to `static/interviews/...`; `PAUSE_S3=true`; data lost on restart and not shared across replicas.
3. **`BackgroundTasks` fallback double-runs at scale** — with 2+ API replicas, each would run the pipeline and double-write results.
4. **`print()` logging** — not structured, not centrally collectable at scale.
5. **Default `admin@example.com / admin123` seed** on every boot — must never happen in prod.
6. **CORS `["*"]`** in Render config — tighten to real domains.
7. **Frontend hardcodes `http://{hostname}:5001/api`** fallback (`constants.ts:8`) — prod must be HTTPS via env.
8. **Long-lived AWS creds in env** (`s3.py`) — switch to IAM task-role credentials.

---

## 3. Phase 2 — Target AWS Architecture

### 3.1 Service Map

```
                      Internet
                         │ (443)
                    ┌────▼─────┐
                    │ Route 53 │   (prod only; staging uses ALB DNS)
                    └────┬─────┘
                         │
                 ┌───────▼────────┐   WAF (prod, optional)
                 │  ALB (x2 AZs)  │   ACM cert, 80→443 redirect
                 └────┬──────┬────┘
        /api /voice /ws  │      │ (everything else)
                 ┌──────▼──┐ ┌──▼───────────┐
                 │  Next   │ │   FastAPI    │   ECS Fargate, private subnets
                 │  :3000  │ │   :5000      │   2+ replicas, autoscaling
                 └─────────┘ └──┬──────┬────┘
                    Celery      │      │
                    Worker ─────┘      │   same image, `worker` command, private subnets
              ┌───────────────────▼────▼──────────────┐
              │ RDS PostgreSQL  ·  ElastiCache Redis  │   DB subnet group, private
              └───────────────────────────────────────┘
   Outbound via NAT Gateway → Groq/OpenAI/Gemini/SendGrid/ncert.nic.in
   S3 via VPC Gateway Endpoint (no NAT egress needed for S3)
```

### 3.2 Required AWS Services & Justification

| Service | Why (grounded in the codebase) |
|---|---|
| **Amazon ECS on Fargate** | Runs the three containerized workloads — Next.js (3000), FastAPI (5000, incl. WebSocket), Celery worker — with no EC2 fleet management. |
| **Application Load Balancer (ALB)** | Single ingress routing `/api`, `/voice`, `/static` + WebSocket to FastAPI and the rest to Next.js; health checks; TLS termination; zero-downtime deploys. |
| **Amazon Route 53** | DNS for the prod domain and per-school/student URLs. |
| **AWS Certificate Manager (ACM)** | Free managed TLS on the ALB (frontend currently assumes `http://`). |
| **Amazon RDS PostgreSQL** | Persistent home for all tables; Multi-AZ (prod), automated backups, PITR, KMS encryption. |
| **Amazon ElastiCache Redis** | Real Celery broker/backend (`CELERY_BROKER_URL`); eliminates the `BackgroundTasks` fallback. |
| **Amazon S3** | Shared, durable media: student pictures, interview audio, TTS cache, textbook PDFs; Lifecycle-managed. |
| **Amazon ECR** | Private container registry for the two images built in CI/CD. |
| **AWS SSM Parameter Store** | Stores `SECRET_KEY`, LLM/SendGrid/AWS keys, RDS creds; **free** standard tier; injected as env. (Upgrade to Secrets Manager only if auto-rotation is needed later.) |
| **AWS IAM** | Least-privilege execution + task roles (ECR pull, CloudWatch logs, S3, SSM read). |
| **Amazon VPC + NAT Gateway** | Public/private subnets across AZs; egress for LLM/SendGrid/NCERT calls. |
| **Amazon CloudWatch** | Logs, Container Insights metrics, alarms (5xx, latency, queue depth, DB health). |
| **CloudFront (prod, optional)** | CDN for static assets + media; clean S3 access via OAC. |
| **AWS WAF (prod, optional)** | Rate limiting + OWASP managed rules in front of the ALB. |
| **CodePipeline/CodeBuild or GitHub Actions** | Build → test → ECR push → migrate → Blue/Green deploy. |
| **AWS X-Ray (optional)** | Trace the 11-step pipeline + each LLM call for latency diagnosis. |
| **Amazon SNS** | Alarm fan-out to email/Slack (Ops notifications). |
| **S3 + DynamoDB (Terraform state)** | Remote state store + locking for IaC. |

---

## 4. Phase 0 — Code Preconditions

All changes below are required **before** any AWS workload runs. Each is a contained,
independently shippable change.

### 4.1 Migrations → Alembic (blocker #1)

**Problem:** `main.py:9-249` runs `Base.metadata.create_all` plus ~40 inline `ALTER TABLE`
statements and seeds on **every boot**.

**Plan:**

1. Author a baseline Alembic migration that recreates the current schema (all tables +
   columns produced by the inline migration block).
2. Move the V2 compiler / review / session columns into the baseline as well.
3. Replace the `main.py` migration block with a single idempotent `ensure_db_ready()` that
   only runs `create_all` as a last-resort guard in non-prod, plus `alembic upgrade head`.
4. Move admin seeding behind `APP_ENV != production` and drive credentials via env/secrets
   (never `admin123`).
5. Move NCERT seeding to an explicit, idempotent management command.

**Acceptance criteria:** On a fresh RDS database, `alembic upgrade head` alone produces the
full schema; app boot performs no DDL.

### 4.2 Media → S3 (blocker #2)

**Problem:** `save_uploaded_audio` writes to `static/interviews/{id}/q{n}.wav` (task-local
disk); `PAUSE_S3=true` redirects all S3 writes locally; `s3.py` uses long-lived creds and
sets `public-read`.

**Plan:**

1. Introduce a `MediaStore` abstraction (`infrastructure/storage.py`) with a single
   `upload(key, bytes, content_type) -> URL` API.
2. Back it with S3 (prod/staging) and local disk (dev, `PAUSE_S3=true` retained for dev only).
3. Route `save_uploaded_audio`, student `picture_url` uploads, and TTS cache through it.
4. Serve media via **presigned URLs** (private bucket) or **CloudFront OAC** — never
   `public-read`.
5. Drop long-lived creds in prod: boto3 assumes the ECS **task role** when
   `AWS_ACCESS_KEY_ID` is absent.
6. Add S3 lifecycle rules to expire interview audio (replaces `cleanup_expired_audio_task`).

**Acceptance criteria:** A completed interview's audio + a student's picture survive an API
task restart and are fetchable from a private S3 bucket via signed URL.

### 4.3 Disable `BackgroundTasks` fallback on AWS (blocker #3)

**Problem:** `routes.py:160-177` falls back to in-process `BackgroundTasks` when Redis is
unreachable. With 2+ replicas, every replica runs the pipeline → duplicate evaluations.

**Plan:**

1. Gate the fallback: on `APP_ENV in (staging, production)`, **never** use `BackgroundTasks`;
   fail fast with a 503/500 if Celery cannot enqueue.
2. Keep `BackgroundTasks` only for local dev.
3. Add a Celery `on_failure` hook that marks the interview status `Failed` for visibility.

**Acceptance criteria:** With Redis stopped in staging, `POST /interviews/submit` returns an
error rather than silently scheduling in-process.

### 4.4 Structured logging (blocker #4)

**Plan:**

1. Replace `print(...)` (≈40 call sites) with a JSON-formatted `logging` module
   (`infrastructure/logging.py`): timestamps, `interview_id`, `step`, `task`.
2. Keep `flush=True` semantics by setting `PYTHONUNBUFFERED=1` (already in Dockerfile).
3. Ship to CloudWatch Logs.

**Acceptance criteria:** `aws logs tail /ecs/momentum-api` shows structured JSON lines for
pipeline steps.

### 4.5 Frontend URL correctness + CORS (blocker #5/7)

1. `constants.ts:getApiBaseUrl()` — in prod, use `NEXT_PUBLIC_API_URL` (https) and never the
   `http://{hostname}:5001` fallback.
2. `main.py` CORS — load an allow-list from env (`BACKEND_CORS_ORIGINS`), no wildcard in prod.
3. Ensure `NEXT_PUBLIC_API_URL` is baked at **build time** in CI (Next.js public envs are
   inlined).

### 4.6 Config & secrets cleanup (blocker #6/8)

1. Add to `common/config.py`: `APP_ENV`, `S3_BUCKET_MEDIA`, `S3_BUCKET_REPORTS`,
   `LOG_LEVEL`, `TASK_MODE` (`celery` | `background`).
2. All secrets come from SSM Parameter Store in AWS; `.env` remains dev-only.
3. Remove default credential values that silently enable insecure modes.

---

## 5. Infrastructure as Code (Terraform)

### 5.1 Repository Layout

```
terraform/
├── main.tf                 # provider config, backend wiring
├── providers.tf            # aws, random, null providers
├── versions.tf             # required_version, provider pins
├── outputs.tf              # ALB DNS, bucket names, secret ARNs
├── variables.tf            # env-scoped variables
├── modules/
│   ├── vpc/                # VPC, 2-3 AZs, public/private/db subnets, NATs, S3 endpoint
│   ├── ecs/                # cluster, task defs, services, autoscaling, CodeDeploy
│   ├── rds/                # Postgres instance, subnet group, backups, KMS
│   ├── redis/              # ElastiCache, encryption, security group
│   ├── s3/                 # media + reports buckets, KMS key, lifecycle
│   ├── params/             # SSM Parameter Store (free) — secrets/config
│   ├── iam/                # execution + task roles, policies
│   └── alb/                # load balancer, target groups, listeners, ACM, WAF
└── envs/
    ├── staging/
    │   ├── backend.tf      # s3 backend: momentum-tf-state/staging
    │   └── staging.tfvars
    └── prod/
        ├── backend.tf      # s3 backend: momentum-tf-state/prod
        └── prod.tfvars
```

### 5.2 Terraform State

- Remote backend in S3 (`momentum-tf-state`) with `enable_versioning=true`, default deny.
- DynamoDB table `terraform-locks` for state locking.
- One workspace/path per environment (`staging`, `prod`) to isolate blast radius.
- State bucket + lock table bootstrapped once via `terraform-bootstrap/`.

### 5.3 Module Detail

#### `modules/vpc`

| Resource | Detail |
|---|---|
| `aws_vpc` | CIDR `10.0.0.0/16`, DNS support + hostnames enabled |
| Subnets | Public x2 (staging) / x3 (prod), private x2/x3, db x2/x3 |
| NAT | 1 (staging, shared) / 2 (prod, one per AZ) in public subnets |
| `aws_vpc_endpoint` | `s3` Gateway endpoint (media without NAT egress) |
| Flow logs (prod) | To CloudWatch Logs for audit |

#### `modules/ecs`

| Resource | Detail |
|---|---|
| `aws_ecs_cluster` | `momentum-{env}` |
| Task defs | `next` (3000), `api` (5000), `worker` (Celery) |
| Logging | `awslogs` driver → CloudWatch, JSON format, retention 14/90 days |
| Secrets | `environment` from SSM Parameter Store via `valueFrom` |
| Services | API x2 (staging) / x3 (prod); Next x2/x3; worker x1/x2 |
| Autoscaling | Target CPU 70%; min/max per env; worker scales on queue depth (custom metric) |
| Deployment | Blue/Green via CodeDeploy (API + worker); Rolling `min 100% / max 200%` for Next |
| Capacity | Fargate Spot for worker (cost); on-demand for API/Next |

#### `modules/rds`

| Resource | Staging | Prod |
|---|---|---|
| Engine | PostgreSQL 15 | PostgreSQL 15 |
| AZs | single-AZ | Multi-AZ |
| Instance | db.t4g.small | db.t4g.medium (start) |
| Storage | 20 GiB gp3, auto-scale on | 50 GiB gp3, auto-scale on |
| Backups | 7 days, PITR on | 7 days, PITR on |
| Security | KMS encrypted, deletion protection, no public access | same |
| Connectivity | `pool_pre_ping` already in app | same |

#### `modules/redis`

- `aws_elasticache_cluster` redis 7.x, single node (staging) / multi-AZ (prod).
- `transit_encryption_enabled=true`, `at_rest_encryption_enabled=true`.
- SG allows 6379 from ECS/Worker SGs only.
- Used as Celery broker only (result backend TTL short or disabled — reports persist to RDS).

#### `modules/s3`

- Buckets: `momentum-{env}-media`, `momentum-{env}-reports`.
- SSE-KMS (shared KMS key).
- Lifecycle: `Standard-IA` after 30d; audio `Expire` after 90d (replaces
  `cleanup_expired_audio_task`).
- Bucket policy: allow only task role; block public access.
- Access: presigned URLs in-app; CloudFront OAC for static media (prod).

#### `modules/params` (SSM Parameter Store — free)

- Parameters (one per secret/config, standard tier = $0):
  - `momentum/{env}/SECRET_KEY`
  - `momentum/{env}/GROQ_API_KEY`
  - `momentum/{env}/OPENAI_API_KEY`
  - `momentum/{env}/GEMINI_API_KEY`
  - `momentum/{env}/SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`
  - `momentum/{env}/DB_*` (RDS creds)
- Task definitions reference them via `valueFrom` (injected as env vars).
- KMS key for encrypted parameters; policies scoped to execution role.

#### `modules/alb`

| Resource | Detail |
|---|---|
| Listener rules | `/api`, `/voice`, `/static` → FastAPI TG; `/` → Next TG |
| Certificates | ACM cert for `<domain>` |
| WebSocket | ALB supports WS natively (upgrade header passes through) |

#### `modules/iam`

| Role | Grants |
|---|---|
| `ecsExecutionRole` | ECR pull, CloudWatch logs, SSM Parameter Store read (param-ARN-scoped) |
| `ecsTaskRole` | S3 (bucket-scoped get/put), CloudWatch metrics, X-Ray (optional), SES (future) |
| CI/CD deploy role | ECR push, ECS update, CodeDeploy, S3 state, DynamoDB lock |

### 5.4 `terraform apply` Order

```bash
# bootstrap state (once)
cd terraform-bootstrap && terraform apply

# deploy an environment
cd terraform/envs/staging
terraform init -backend-config=backend.tf
terraform plan  -var-file=staging.tfvars
terraform apply -var-file=staging.tfvars
```

Dependency order is handled by Terraform graph (VPC → IAM → RDS/Redis/S3/Secrets → ECS/ALB).

---

## 6. Network & Security Architecture

### 6.1 VPC Layout

```
10.0.0.0/16
├── Public subnets (2-3 AZs)     → ALB, NAT Gateways
├── Private app subnets (2-3)    → ECS tasks (next, api, worker)
└── DB subnets (2-3)             → RDS, ElastiCache
```

### 6.2 Security Groups

| SG | Inbound | Outbound |
|---|---|---|
| `alb` | 443/80 from 0.0.0.0/0 | app subnets only |
| `ecs-next` | 3000 from `alb` SG | via NAT |
| `ecs-api` | 5000 from `alb` SG | via NAT |
| `ecs-worker` | none | via NAT |
| `rds` | 5432 from `ecs-api` + `ecs-worker` SGs | none |
| `redis` | 6379 from `ecs-api` + `ecs-worker` SGs | none |

- **No public RDS/Redis.** No bastion — use ECS Exec (`aws ecs execute-command`) or SSM
  Session Manager for debugging.
- **TLS:** ACM cert on ALB, HTTP→HTTPS redirect. In-app CORS allow-list, no wildcard.
- **IAM least-privilege:** roles above; no `AdministratorAccess`; credentials rotated;
  no long-lived access keys in prod containers.

### 6.3 Secrets & Configuration Handling

- All env + secrets live in SSM Parameter Store; task definitions reference via `valueFrom`.
- RDS credentials stored in SSM (Secrets Manager rotation can be adopted later if required).
- `SECRET_KEY` is a standalone parameter, rotated independently.
- No `.env` files are baked into images; `.dockerignore` excludes them.

---

## 7. Data & State Management

| Concern | Strategy |
|---|---|
| Relational data | RDS PostgreSQL — Multi-AZ (prod), encrypted, 7d PITR, deletion protection |
| Media/files | S3 private buckets (SSE-KMS) + presigned URLs; CloudFront OAC in prod |
| TTS cache | S3 (`tts-cache/`) with TTL lifecycle; cache keys already SHA-256 based |
| Celery broker | ElastiCache Redis, encrypted; short-lived result backend |
| Auth sessions | Stateless JWT (client-side). Optional: Redis token blacklist for logout/revoke |
| Secrets | SSM Parameter Store (free); injected as env. Adopt Secrets Manager only for rotation |
| Migrations | `alembic upgrade head` as a one-off ECS task in the pipeline, **before** deploy |
| Seeding | Idempotent, env-guarded; never seeds `admin123` in prod |
| Backups (media) | S3 versioning + replication (prod) |

### 7.1 Migration Strategy for Existing Data

1. Freeze writes during cutover window.
2. `pg_dump` from Render Postgres → restore into RDS staging.
3. Migrate media: script `download_from_s3` / copy `static/` → S3 media bucket.
4. Verify counts (`interviews`, `student_assessments`, `evaluation_steps`) match.
5. Flip frontend `NEXT_PUBLIC_API_URL` to new domain.
6. Keep Render read-only as rollback for 72h.

---

## 8. CI/CD & Deployment Pipeline

### 8.1 Pipeline (GitHub Actions)

```
on: push → main  (and release/* for prod)

Job lint:
  - eslint (frontend) · ruff/flake8 (backend)

Job test:
  - next build
  - pytest tests/            # existing suite; tests use SQLite via config auto-detection

Job build:
  - docker build backend → push momentum-backend:{sha} to ECR
  - docker build frontend → push momentum-frontend:{sha} to ECR

Job infra (per environment):
  - terraform init/plan/apply (state per env)

Job migrate:
  - run one-off ECS task: alembic upgrade head   (must pass before deploy)

Job deploy:
  - CodeDeploy Blue/Green (api + worker): create new TG, wait for health, swap, rollback on fail
  - Rolling update (next)

Job verify:
  - smoke test via ALB: GET / (health), POST /auth/login, GET /reports/overview
```

### 8.2 Deployment Strategy

| Service | Strategy | Zero downtime |
|---|---|---|
| FastAPI | **Blue/Green** via CodeDeploy | Yes — swap TG on health pass, auto-rollback |
| Celery worker | **Blue/Green** (same image, `worker` cmd) | Yes |
| Next.js | **Rolling** `minHealthyPercent=100, maxPercent=200` | Yes |

- Immutable image tags (`{sha}`), never `latest`.
- Environment promotion: `staging` → `prod` by applying the same Terraform modules with
  prod tfvars; images promote via same `{sha}`.

### 8.3 Branch Strategy

- `main` → staging deploy.
- `release/*` (tag) → prod deploy.
- PRs → lint + test only.

---

## 9. Observability & Monitoring

### 9.1 Baseline

| Category | Tool |
|---|---|
| Logs | CloudWatch Logs (`/ecs/momentum-{env}/{service}`), structured JSON, 14d (staging) / 90d (prod) retention |
| Metrics | CloudWatch Container Insights (CPU, memory), ALB request count / p95 / 5xx |
| Alarms → SNS | Email + Slack channel |
| Errors | Sentry (free tier) — no error tracker exists today |
| Tracing (optional) | AWS X-Ray around the 11-step pipeline + LLM calls |
| Worker health | Celery task success/failure rate; queue depth metric |

### 9.2 Recommended Alarms

| Alarm | Metric / condition |
|---|---|
| API 5xx | ALB 5xx > 1% over 5 min |
| API latency | p95 > 2s over 5 min (LLM-bound steps skew this — alert, don't page) |
| Unhealthy targets | ALB healthy host count < min |
| DB CPU | > 80% over 10 min |
| DB storage | free storage < 20% (auto-scale should handle) |
| Redis memory | > 80% over 10 min |
| **Celery queue depth** | backlog > N for M min → scale workers / alert |
| Failed eval tasks | CloudWatch metric from Celery `on_failure` hook |
| Pipeline step failure | `interview_evaluation_steps.status = Failed` count > 0 |

### 9.3 Logging Standards

- JSON, one line per event: `{ts, level, logger, env, service, interview_id?, step?, task_id?}`.
- Never log secrets/transcripts at INFO.
- Sanitize LLM prompt/response payloads at DEBUG only.

---

## 10. Environments & Cost Posture

> **Lean startup posture:** see [`aws_requirements.md`](./aws_requirements.md) — the minimal,
> cloud-agnostic service set. Default to the **staging** shape for the first prod launch and
> only add Multi-AZ / CloudFront / WAF / X-Ray when a concrete need exists.

| Env | Shape | Approx monthly cost |
|---|---|---|
| `dev` | Local / docker-compose only | $0 |
| `staging` | 2 AZs, single-AZ RDS (t4g.micro), 1-node Redis (t4g.micro), Fargate next 0.25 / api 0.5 / x1 spot worker, 1 NAT, SSM (free) | ~$85–140 |
| `prod` (lean start) | Same as staging + autoscaling; single-AZ RDS w/ PITR, 1 NAT | ~$125–160 |
| `prod` (hardened, later) | Multi-AZ RDS, 2nd NAT, CloudFront, WAF, X-Ray, Secrets Manager rotation | ~$350–550 |

**Cost levers:** Fargate Spot workers; scale-to-min outside school hours (scheduled
scaling); single-AZ RDS with PITR for non-critical tenants; retire unused media via
lifecycle; SSM Parameter Store instead of Secrets Manager.

---

## 11. Rollout Plan (credential-gated)

> **You don't need AWS creds until Phase 1.** Phase 0 is pure local code work. Create the AWS
> account + IAM creds (aws_requirements.md Stage B) in parallel with Phase 0, and have them
> ready when Phase 0 exits.

| Phase | AWS creds needed? | Scope | Exit criteria |
|---|---|---|---|
| **0 — Code prep** | **No** | Alembic consolidation, S3 media (`MediaStore`), kill background fallback, structured logs, frontend URL/CORS, config/secrets, Dockerfile hardening, Terraform skeleton (fmt/validate only) | All acceptance criteria in §4 pass; CI green; TF code written + validated locally |
| **0.5 — AWS account + creds** | — | Create account, MFA on root, IAM admin user, billing alarm, `aws configure` | `aws sts get-caller-identity` returns your IAM user |
| **1 — Staging build** | **Yes** | Terraform bootstrap + modules, staging env, SSM params, ECS services, ALB, RDS, Redis, S3 | `terraform apply` staging succeeds; app healthy at ALB DNS; 2 API replicas safe |
| **2 — CI/CD** | **Yes** (as GitHub Secrets) | GitHub Actions full pipeline to staging; migration task; Blue/Green | Push to `main` auto-deploys staging with zero downtime |
| **3 — Data migration** | **Yes** | pg_dump restore; media copy; verify; flip DNS | Staging copy verified; rollback ready |
| **4 — Prod hardening** | **Yes** | 3 AZ, Multi-AZ RDS, CloudFront + WAF, Route 53, autoscaling, scheduled scaling | Prod traffic served; alarms wired; Blue/Green verified |
| **5 — Observability** | **Yes** | Sentry, X-Ray, dashboards, runbook drills | Dashboards live; on-call drill passed |

**Sequencing notes:**

- Phase 0.1 (Alembic) is the first code change — everything downstream depends on a clean
  migration story.
- **Phases 0 and 0.5 run in parallel** — the AWS signup/credential paperwork takes days
  (account approval, billing, IAM), so start it the same day as Phase 0 code work.
- Phases 1–5 are strictly sequential and all require credentials.

---

## 12. Runbooks

### 12.1 Report pipeline stuck ("Evaluation Running" forever)

1. Check Celery queue depth (CloudWatch alarm) and worker logs
   (`aws logs tail /ecs/momentum-prod/worker --follow`).
2. If worker down: check task health, restart service via ECS; confirm Redis reachable.
3. If task failed on retries: inspect `interview_evaluation_steps.error`; regenerate via
   `POST /interviews/{id}/regenerate`.

### 12.2 Deploy rollback

1. Blue/Green auto-rolls back on health-check failure; confirm in CodeDeploy console.
2. Manual rollback: redeploy previous image tag (`git revert` → pipeline → old `{sha}`).
3. DB: migrations are forward-only; if a migration broke, restore from PITR snapshot (data
   loss window = snapshot age).

### 12.3 RDS failover / maintenance

1. Multi-AZ failover is automatic; app uses `pool_pre_ping` so connections recover.
2. Verify `SECRET_KEY`/DB secrets rotate cleanly during maintenance windows.

### 12.4 LLM provider outage (Groq/OpenAI/Gemini all down)

1. Pipeline falls back to local heuristic (by design, `generator.py`).
2. Alarms on fallback usage; temporarily lower quality expectations; check provider status.
3. Regenerate reports later via admin endpoint once providers recover.

### 12.5 Restore media

1. S3 versioning: restore previous version via console/CLI.
2. RDS: `aws rds restore-db-instance-to-point-in-time` to a new instance; flip connections.

---

## 13. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Inline migrations conflict on RDS | Med | High | Alembic consolidation first (Phase 0) |
| Duplicate evaluations from multi-instance | Med | High | Disable `BackgroundTasks` on AWS; Celery-only |
| Media loss on task restart | High | High | S3 + presigned URLs before any scale-out |
| `admin123` default creds on prod | Low | Critical | Env-guarded seeding; SSM Parameter Store creds |
| CORS wildcard | Med | Med | Allow-list from env; no `*` in prod |
| LLM cost spikes | Med | Med | Caching, rate limits, alerts on spend |
| JWT 7-day expiry UX | Med | Low | Rotation/refresh flow later; Redis blacklist option |
| Locked TF state | Low | Med | DynamoDB locking; drift detection in CI |
| WebSocket through ALB | Low | Med | ALB supports WS natively; test upgrade header |
| Sentry/observability gap on launch | Med | Med | Wire Sentry + alarms in Phase 5 before prod cutover |

---

## 14. Appendix — Supporting Details

### 14.1 Key Files Touched (Phase 0)

| File | Change |
|---|---|
| `backend/app/main.py` | Remove inline migration/seed block → `alembic upgrade head` + guarded seeds |
| `backend/alembic/` | Baseline migration(s) authoring |
| `backend/app/ai_assessment/audio/router.py` | `save_uploaded_audio` → `MediaStore` |
| `backend/app/infrastructure/s3.py` | IAM task-role creds, no public ACL, `MediaStore` |
| `backend/app/api/interviews/routes.py` | Gate `BackgroundTasks` fallback to dev |
| `backend/app/tasks/evaluation_tasks.py` | `on_failure` hook; structured logs |
| `backend/app/common/config.py` | `APP_ENV`, `S3_BUCKET_*`, `LOG_LEVEL`, `TASK_MODE` |
| `backend/app/common/logging.py` (new) | JSON formatter |
| `frontend/src/utils/constants.ts` | HTTPS env-driven base URL in prod |
| `backend/app/main.py` (CORS) | Allow-list from env |

### 14.2 Celery Worker Command (ECS)

```
# same image as API, override command:
celery -A app.core.celery_app.celery_app worker --loglevel=info --concurrency=4
```

### 14.3 Health Check Endpoints

| Service | Health check |
|---|---|
| Next.js | `GET /` → 200 |
| FastAPI | `GET /` → `{"status": "healthy"}` (already implemented) |
| Worker | Celery ping / queue depth metric |

### 14.4 Security Checklist (pre-prod)

- [ ] No public RDS/Redis; SGs allow only app SGs
- [ ] ACM TLS on ALB; HTTP→HTTPS redirect
- [ ] CORS allow-list; no `*`
- [ ] IAM least-privilege; no long-lived creds in containers
- [ ] Secrets rotated; `SECRET_KEY` not default
- [ ] S3 private + SSE-KMS; no `public-read`
- [ ] RDS encrypted, deletion protection, PITR
- [ ] Container images immutable, non-root user where possible
- [ ] WAF attached (prod)
- [ ] Backups verified by restore drill

### 14.5 Suggested Next Actions

1. Approve this plan + [`aws_requirements.md`](./aws_requirements.md) (minimal service set).
2. Start **Phase 0.1 — Alembic consolidation**.
3. Parallel: stand up `terraform-bootstrap` (state bucket + lock table) and empty module
   skeletons.
4. Complete §14.4 checklist before prod cutover.
