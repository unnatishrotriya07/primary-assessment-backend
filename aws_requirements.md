# AWS Requirements for Momentum (Startup Minimal Set)

**Status:** Proposed (v1)
**Date:** 2026-08-22
**Owner:** Platform Engineering
**Context:** Companion to [`cloud_implementation.md`](./cloud_implementation.md) — a lean,
cost-minimal, cloud-agnostic AWS footprint for a startup. Only what we need, configured small,
able to scale without re-architecture.

> **Guiding principles**
> 1. **Minimal cost** — use free tiers and the smallest managed instances that work; defer
>    anything that doesn't earn its keep; no throwaway services.
> 2. **Clean** — one job per service; managed services over self-hosting; everything via
>    Terraform (no click-ops); no unused resources.
> 3. **Scalable** — every service we pick can grow (managed scaling) without a redesign.
> 4. **Cloud-agnostic** — app code must not depend on AWS APIs except through one thin
>    abstraction (`MediaStore` for S3). Everything else already uses standard drivers/HTTP.

---

## 1. What the app actually needs (recap)

| Need | Current code | Cloud-agnostic? |
|---|---|---|
| Web server (Next.js) | `next start` :3000 | Yes — plain Node container |
| API (FastAPI) | `uvicorn` :5000, REST + WebSocket | Yes |
| Worker (Celery) | `evaluate_interview_task`, `sync_ncert_chapter_task` | Yes — broker via URL |
| Database | SQLAlchemy → PostgreSQL 15 | Yes — `DATABASE_URL` |
| Queue/broker | Celery → Redis | Yes — `CELERY_BROKER_URL` |
| Object storage | boto3/S3, gated by `PAUSE_S3` | **No — only AWS coupling** → isolate behind `MediaStore` |
| Secrets/env | `.env` (dev) → secrets on cloud | Yes — env-var injection |
| Email | SendGrid (HTTP) | Yes — external SaaS |
| LLMs | Groq / OpenAI / Gemini (HTTP) | Yes — external SaaS |
| NCERT PDFs | `ncert.nic.in` (HTTP fetch) | Yes — external |

**Conclusion:** the only AWS-specific dependency in the application is **S3** (boto3). Everything
else is portable. Keeping S3 behind a `MediaStore` abstraction (already planned in
`cloud_implementation.md` §4.2) means we can move to GCS/Azure Blob later with one backend swap.

---

## 2. Core AWS services (set these up)

### Must-have — run the app

| # | Service | Why (grounded in code) | Startup config | Est. cost/mo |
|---|---|---|---|---|
| 1 | **Amazon VPC** | Private network: public subnets (ALB), private app subnets (ECS), DB subnets (RDS/Redis) | 2 AZs, CIDR `10.0.0.0/16`, 1 NAT gateway | ~$32 (NAT) |
| 2 | **Amazon ECS on Fargate** | Runs the 3 containerized workloads: `next` (3000), `api` (5000 + WS), `worker` (Celery) | `next`: 0.25 vCPU/0.5 GB · `api`: 0.5 vCPU/1 GB · `worker`: 1 vCPU/2 GB on **Fargate Spot** | ~$40–50 |
| 3 | **Amazon ECR** | Private registry for the 2 images built in CI/CD | 2 repos (`momentum-backend`, `momentum-frontend`); lifecycle to expire old tags | ~$0–1 |
| 4 | **Application Load Balancer** | Single ingress: `/api`, `/voice`, `/static` + WebSocket → FastAPI; `/` → Next; health checks; TLS termination; zero-downtime deploys | 1 ALB, 2 target groups, idle timeout 60s (default) | ~$18–22 |
| 5 | **AWS Certificate Manager (ACM)** | Free managed TLS on the ALB (frontend currently assumes `http://`; must be HTTPS) | 1 cert for the domain | $0 |
| 6 | **Amazon Route 53** | DNS for the app domain (hosted zone) | 1 hosted zone, A/ALIAS records | ~$0.50 + domain (~$12/yr) |
| 7 | **Amazon RDS PostgreSQL** | The primary datastore — all 13+ tables (interviews, student_assessments, evaluation_steps, …) | **single-AZ**, `db.t4g.micro`, 20 GiB gp3, PITR backups on (7d), KMS encryption, deletion protection | ~$14 (free tier first 12 mo if eligible) |
| 8 | **Amazon ElastiCache Redis** | Real Celery broker/backend (`CELERY_BROKER_URL`) — replaces the fragile `BackgroundTasks` fallback | `cache.t3.micro` (or `t4g.micro`), encryption in transit + at rest | ~$12 |
| 9 | **Amazon S3** | Media + files: student pictures, interview audio, TTS cache, textbook PDFs. Replaces task-local `static/` and `PAUSE_S3` | 1 bucket (prefixes `media/`, `tts-cache/`), SSE-KMS, private, lifecycle (audio expire ~90d) | ~$0–3 |
| 10 | **AWS SSM Parameter Store** | Free secrets/config store: `SECRET_KEY`, `GROQ/OPENAI/GEMINI_API_KEY`, `SENDGRID_*`, DB creds. Injected as env via `valueFrom`. **Choose this over Secrets Manager to keep cost at $0** | Standard tier (free), one parameter per secret | **$0** |
| 11 | **AWS IAM** | Least-privilege: ECS execution role (ECR pull, logs, param read), ECS task role (S3 bucket-scoped), CI/CD deploy role | 3 roles, scoped policies | $0 |
| 12 | **Amazon CloudWatch** | Central logs (structured JSON from the app), Container Insights metrics, and alarms | Log groups retention **7–14 days**; ~6 alarms | ~$3–8 |
| 13 | **Amazon SNS** | Alarm fan-out to email (Ops notifications) | 1 topic + email subscription | ~$0 |
| 14 | **DynamoDB (Terraform lock)** | State locking for Terraform (infra only, not app) | 1 table `terraform-locks` | ~$0–1 |

### Infra plumbing (one-time, cheap)

| Service | Why | Config |
|---|---|---|
| **S3 bucket for Terraform state** | Remote state + versioning for IaC | `momentum-tf-state`, versioning on, default deny |
| **CloudWatch Logs** | Already covered by #12 | — |

---

## 3. Optional / deferred (do NOT set up yet)

| Service | When to add | Why deferred |
|---|---|---|
| **AWS WAF** | After real traffic / public launch feedback | ~$5+/mo + per-request; ALB + SG + app auth covers us for now |
| **Amazon CloudFront** | When static/media traffic justifies a CDN | Free tier exists but adds complexity; S3 presigned URLs work today |
| **AWS X-Ray** | When LLM-latency debugging becomes a real pain | Free tier exists; structured logs cover most needs first |
| **AWS Secrets Manager** | When you need automated secret **rotation** | $0.40/secret/mo + API calls; SSM Parameter Store is free and sufficient now |
| **Multi-AZ RDS / 3 AZs / 2nd NAT** | At real production scale | Doubles DB/networking cost; single-AZ + PITR is fine for startup |
| **Elastic File System (EFS)** | Only if a shared POSIX FS is ever required | We're removing all task-local disk; not needed |
| **EKS (Kubernetes)** | Never at this scale | Fargate is simpler and cheaper to operate |
| **GPU instances** | Never | Whisper/Kokoro are deprecated stubs; STT/TTS run in-browser |

---

## 4. Non-AWS dependencies (external, already used)

These are **not** AWS services but the app calls them; account for them in config/secrets:

| Service | Purpose | Where |
|---|---|---|
| Groq API | Primary LLM (`llama-3.3-70b-versatile`) + pipeline | `GROQ_API_KEY` |
| OpenAI API | Fallback LLM (`gpt-4o-mini`) | `OPENAI_API_KEY` |
| Google Gemini | Fallback LLM (`gemini-2.0-flash`) | `GEMINI_API_KEY` |
| SendGrid | Assessment invitation emails | `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` |
| ncert.nic.in | Textbook PDF ingestion | outbound HTTP |

---

## 5. IAM essentials (least privilege, $0)

| Role | Permissions |
|---|---|
| `ecsExecutionRole` | ECR pull, CloudWatch logs, SSM Parameter Store read (param-ARN-scoped) |
| `ecsTaskRole` | S3 `Get/Put` on the media bucket only, CloudWatch metrics |
| `ciDeployRole` | ECR push, ECS update, CodeDeploy, S3 state, DynamoDB lock |
| Human admins | No `AdministratorAccess`; scoped per-role; **no long-lived access keys in containers** |

---

## 6. Security baseline (baked in, not optional)

- RDS + Redis in **private subnets**, reachable only from ECS security groups (no public access).
- ALB terminates TLS (ACM); HTTP→HTTPS redirect; CORS allow-list from env (no `*` in prod).
- S3 bucket private + SSE-KMS; **no `public-read` ACL** (remove from `s3.py`).
- Secrets via SSM Parameter Store, referenced by `valueFrom` — never baked into images.
- No bastion host: debug via ECS Exec / SSM Session Manager.
- One NAT gateway to start (add a second per-AZ only when traffic/HA demands it).

---

## 7. Cloud-agnostic checklist

- [ ] S3 calls only via `MediaStore` abstraction (`infrastructure/storage.py`) — swapping to GCS/Azure Blob is a one-file change.
- [ ] No AWS SDK calls anywhere else in app code (boto3 is the only one today).
- [ ] DB via SQLAlchemy + `DATABASE_URL` (already portable across Postgres providers).
- [ ] Redis via `redis-py` URL (portable).
- [ ] Celery as broker-agnostic queue (Redis today; SQS/RabbitMQ possible later).
- [ ] Secrets/params injected as **environment variables** (SSM → env at task start), so the app never reads AWS APIs directly.
- [ ] Infrastructure in Terraform (portable to other clouds; only the AWS provider differs).
- [ ] Frontend talks to the API over HTTPS via `NEXT_PUBLIC_API_URL` (no hostname/port hacks).

---

## 8. Setup order (credential-gated)

> **You do not need AWS credentials to start.** Stage A is pure code work, done locally in the
> repo. Only Stage B onward touches AWS. The gate between A and B is **you creating the AWS
> account + IAM credentials** — that is the one manual prerequisite.

### Stage A — Code prep (NO AWS creds needed · do first)

```text
A1. Alembic consolidation        — remove inline ALTER TABLE block from main.py (cloud plan §4.1)
A2. MediaStore abstraction       — S3 behind infrastructure/storage.py (§4.2)
A3. Disable BackgroundTasks      — Celery-only on AWS env (§4.3)
A4. Structured logging           — JSON logging module (§4.4)
A5. Config & secrets cleanup     — APP_ENV, SSM-ready env vars (§4.6)
A6. Frontend URL + CORS          — NEXT_PUBLIC_API_URL / https, allow-list (§4.5)
A7. Dockerfile hardening         — multi-stage, non-root user, immutable tags
A8. Terraform skeleton           — write modules in repo (terraform/), dry-run only (terraform fmt/validate)
```

**Exit:** all §4 acceptance criteria pass, CI (lint+test) green, and the Terraform code is
written and validated — all without ever calling AWS.

### Stage B — AWS account + credentials (manual, blocks everything below)

```text
B1. Create AWS account (root)             — signup at aws.amazon.com
B2. Turn on MFA on the root account       — required before anything else
B3. Create an IAM admin user for yourself — NOT root; attach AdministratorAccess to that user only
B4. Set a billing alarm                   — Budgets → email alert at ~$25/mo
B5. Install AWS CLI (brew install awscli) + configure `aws configure` with the IAM user keys
B6. (Optional) terraform CLI (brew install terraform)
```

**Creds to have ready:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`
(use `us-east-1` for lowest prices). Do **not** share root creds; store the IAM user keys in a
password manager.

### Stage C — Infrastructure up (AWS creds needed)

```text
C1. Terraform bootstrap     — S3 state bucket + DynamoDB lock (once)
C2. VPC                    — subnets, NAT, S3 gateway endpoint
C3. RDS PostgreSQL         →  ElastiCache Redis  →  S3 media bucket  →  SSM parameters
C4. ECR repos              — push momentum-backend + momentum-frontend images
C5. ECS cluster + services — next, api, worker
C6. ALB + ACM cert + Route 53 record
C7. CloudWatch alarms + SNS
```

### Stage D — Ship

```text
D1. CI/CD (GitHub Actions) — wire AWS creds as GitHub Secrets; full deploy to staging
D2. Data migration         — pg_dump from Render → RDS; media copy → S3 (cloud plan §7.1)
D3. Flip DNS               — point real domain at the ALB; verify HTTPS end-to-end
```

> **Why A before B:** stages A and B are independent — do A1–A8 in parallel with the AWS
> signup/billing paperwork. Nothing in Stage A changes what you need on the AWS side, and
> nothing in Stage B is wasted if the code still needs work.

### Stage D1 — GitHub Actions secrets (one-time setup)

Workflows live in each repo: `primary-assessment-backend/.github/workflows/` (CI + CD) and
`primary-assessment/.github/workflows/` (CI + CD). They use **OIDC** (no long-lived AWS keys
in GitHub). Add these secrets in **Settings → Secrets and variables → Actions**:

| Secret | Repo | Used for |
|---|---|---|
| `AWS_DEPLOY_ROLE_ARN` | backend + frontend | OIDC-assumed deploy role ARN (created via `modules/iam` or manually) |
| `AWS_REGION` (optional) | both | Defaults to `us-east-1` in the workflow |
| `NEXT_PUBLIC_API_URL_STAGING` | frontend | `https://<staging-domain>/api` baked at build |
| `NEXT_PUBLIC_API_URL_PRODUCTION` | frontend | `https://<prod-domain>/api` baked at build |
| `PRIVATE_SUBNETS` | backend | comma-separated subnet IDs for the migration one-off task |
| `API_SG_ID` | backend | API security group ID for the migration one-off task |

**Workflow behavior:**

- **CI** (both repos): runs on PR + push to `main` — backend: ruff + pytest (Postgres 15
  service); frontend: eslint + `next build`.
- **CD** (both repos): runs on push to `main` → `staging`; `workflow_dispatch` selects the env.
  Backend: build+push backend image → `terraform apply` (staging) → run `alembic upgrade head`
  one-off task → rolling deploy of `api` + `worker`. Frontend: build+push frontend image with
  the right `NEXT_PUBLIC_API_URL` → rolling deploy of `next`.
- Deploys are **Rolling** (`min 100% / max 200%`) for all services — zero downtime without
  CodeDeploy. Blue/Green can be layered on later.

> **Terraform note:** the `aws_ecs_service` `api` uses a Rolling deployment controller (not
> CODE_DEPLOY) so the first cut works with a plain `update-service --force-new-deployment`.
> The one-off migration task uses `aws_ecs_task_definition.migrate` (`alembic upgrade head`).

---

## 9. Cost summary (lean startup)

| Category | Est. $/mo |
|---|---|
| Compute (Fargate: next + api on-demand, worker spot) | ~$40–50 |
| Database (RDS t4g.micro, 20 GB, PITR) | ~$14 (free tier first 12 mo) |
| Cache (ElastiCache t3.micro) | ~$12 |
| Network (1 NAT + ALB + data) | ~$52 |
| DNS + domain | ~$1.50 + domain |
| Storage (S3, ECR, state) | ~$3–5 |
| Observability (CloudWatch logs + alarms) | ~$3–8 |
| Secrets (SSM) + IAM + SNS | $0 |
| **Total** | **~$125–145/mo** (less in year one with free tiers) |

**If you have an eligible new AWS account**, RDS + ALB + CloudWatch free tiers cut this further
(roughly **$85–110/mo**).

---

## 10. Cost control rules

1. One NAT gateway, not two. One AZ of everything unless prod demands HA.
2. Fargate **Spot** for the Celery worker (idempotent, restart-safe).
3. Log retention 7–14 days, not 90.
4. S3 lifecycle: expire interview audio (~90d), Standard-IA after 30d.
5. Scheduled scale-down outside school hours if usage is clearly diurnal.
6. Defer WAF / CloudFront / X-Ray / Secrets Manager until there's a concrete need.
7. Set a **billing alarm** on day one.
