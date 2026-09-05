# Deployment Runbook

> **Operational guide** for deploying Astrolabe to AWS. This is the single
> source of truth for getting the app running in production and keeping it
> there. All container/pipeline files are **implemented and merged** (PR #45):
> Dockerfiles, `docker-compose.yml`, GitHub Actions, `ec2-provision.sh`.
> What remains is **execution** (see § "Prerequisites" → "Execution steps").
> For Terraform infrastructure details, see
> [AWS on-demand deployment](aws-ondemand.md).

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| AWS CLI v2 | ≥ 2.15 | Account access (`aws sso login`) |
| Terraform | ≥ 1.6 | Infra provisioning |
| Docker + Docker Compose | v2 | Local build & EC2 runtime |
| Git | ≥ 2.30 | Source control |
| GitHub repo | `AlbertoVilla87/kgraph` | CI/CD origin |

**AWS account**: new-experience project, Region `eu-north-1` (fixed). IAM
roles for GitHub Actions (OIDC) and EC2 SSM access must already exist — see
Stage 0 in [pipelines](pipelines.md).

---

## 1 — Infrastructure (Terraform)

The Terraform stack lives in `infra/terraform/` and creates:

- **EC2 `t3.xlarge`** (4 vCPU / 16 GiB; AL2023, Docker pre-installed via `user_data`) — default del Terraform
- **Elastic IP** (static public IPv4)
- **Security group** (ports 80/443 open; port 22 closed)
- **Wake Lambda** + function URL + auto-stop EventBridge scheduler
- **S3 + CloudFront** for the frontend SPA (always-on static site)
- **IAM**: EC2 instance profile (SSM), Lambda execution role

### Apply

```bash
cd infra/terraform
terraform init
terraform plan -out=tfplan      # review
terraform apply tfplan
```

After apply, note the outputs:

```
backend_public_ip  = "X.X.X.X"
wake_url           = "https://....lambda-url.eu-north-1.on.aws/"
stop_command       = "aws lambda invoke ..."
frontend_url       = "https://d1234.cloudfront.net"
```

Save the `EC2_INSTANCE_ID` in GitHub repo variables (Settings → Variables →
Repository variables) — the deploy workflow needs it.

---

## 2 — First Deploy (manual)

The first time, SSH or SSM into the EC2 and run the provision script:

```bash
# From your local machine (SSM):
aws ssm send-command \
  --instance-ids "<EC2_INSTANCE_ID>" \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["curl -fsSL https://raw.githubusercontent.com/AlbertoVilla87/kgraph/master/scripts/ec2-provision.sh | bash"]'
```

Or via SSH (if enabled temporarily):

```bash
ssh ec2-user@<PUBLIC_IP>
bash /tmp/ec2-provision.sh
```

What it does:

1. Clones the repo to `~/kgraph`
2. Copies `.env.example` → `.env` (edit if needed)
3. Runs `docker compose pull` (falls back to local build if no ECR images)
4. Starts services with `docker compose up -d`

> **Ollama is required, not optional.** The backend's only analysis pipeline is
> citation-guided discovery, which calls Qwen3 via Ollama. Compose gates the
> container behind the `citation` profile, so deploy with
> `docker compose up -d --profile citation` — without it the UI comes up healthy
> but every analysis job fails (`ensure_ollama()` in the container cannot reach a
> local Ollama).

### Verify

```bash
# From the EC2 or your local machine:
curl http://<PUBLIC_IP>/api/health
# → {"status":"ok"}

# Frontend:
open http://<PUBLIC_IP>
```

The first start is slow (~2–3 min) because the backend loads ML models into
memory. The Docker healthcheck waits up to 120s (`start-period`) before
reporting healthy.

---

## 3 — CI/CD (GitHub Actions)

### Setup (one-time)

1. **Create ECR repos** (Terraform or CLI):

   ```bash
   aws ecr create-repository --repository-name kgraph/backend --region eu-north-1
   aws ecr create-repository --repository-name kgraph/frontend --region eu-north-1
   ```

2. **GitHub secrets** (Settings → Secrets → Actions):

   | Secret | Value |
   |---|---|
   | `AWS_ACCOUNT_ID` | `184463060626` |

3. **GitHub variables** (Settings → Variables → Actions):

   | Variable | Value |
   |---|---|
   | `EC2_INSTANCE_ID` | From `terraform output` |
   | `EC2_PUBLIC_IP` | From `terraform output` |

### Build images → ECR

Triggered by pushing a `v*` tag or manual dispatch:

```bash
git tag v0.1.0
git push --tags
# → .github/workflows/build.yml runs
# → pushes kgraph/backend:v0.1.0 + kgraph/frontend:v0.1.0 to ECR
```

### Deploy to EC2

Triggered manually from the GitHub Actions UI (workflow_dispatch):

```
Actions → deploy → Run workflow → ref: master → Run workflow
```

What it does:

1. Assumes the `github-actions-ssm` IAM role via OIDC
2. Sends a shell command to the EC2 via SSM: `git pull && docker compose up -d`
3. Polls `/api/health` until the backend responds (up to 10 min)

---

## 4 — Day-to-Day Operations

### Wake / stop (on-demand model)

The VM sleeps by default and wakes on the first request. See
[AWS on-demand deployment](aws-ondemand.md) for the Lambda/Scheduler setup.

```bash
# Wake the instance:
curl "<wake_url>"

# Stop manually (auto-stop fires after 3h by default):
aws lambda invoke --function-name kgraph-astrolabe-wake \
  --cli-binary-format raw-in-base64-out \
  --payload '{"action":"stop"}' /dev/stdout
```

### View logs

```bash
# Backend logs (on the EC2):
docker compose logs -f backend

# All services:
docker compose logs -f

# Nginx access logs:
docker compose logs nginx | grep -v "200 OK"
```

### Restart services

```bash
# On the EC2:
cd ~/kgraph
docker compose restart backend    # restart just the backend
docker compose up -d --pull always # pull latest images + recreate
```

### Upgrade (pull new code + rebuild)

```bash
# On the EC2:
cd ~/kgraph
git pull origin master
docker compose up -d --build --remove-orphans
```

Or use the GitHub Actions deploy workflow — it does the same thing remotely.

### Check model status

```bash
# Verify models are baked in:
docker compose exec backend ls -lh /app/models/
# Should show:
#   gliner-relex-large-v0.5/   (~3.5 GB)
```

---

## 5 — Troubleshooting

### Backend won't start

```bash
docker compose logs backend | tail -30
```

Common causes:

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | Image wasn't built from the right context. Rebuild: `docker compose build backend` |
| `OOMKilled` | Instance too small for GLiNER + Ollama. Confirm the instance is `t3.xlarge` (16 GiB); `t3.large` risks OOM on deep runs |
| `HF_HUB_OFFLINE` error | Model not baked into image. Rebuild the image with `docker build` |
| Healthcheck timeout | First start takes 2–3 min (model loading). Wait; check `docker compose logs -f backend` |

### Frontend shows "Cannot connect to API"

```bash
# Check nginx config:
docker compose exec nginx cat /etc/nginx/conf.d/default.conf

# Check backend is reachable from nginx:
docker compose exec nginx curl -s http://backend:8000/api/health
```

### ECS/EC2: "Permission denied" on ECR pull

The EC2 instance profile needs `AmazonEC2ContainerRegistryReadOnly`. Verify:

```bash
aws iam list-attached-role-policies --role-name <instance-role>
```

### CORS errors in browser

`main.py` defaults to `http://localhost:5173`. In production (same-origin via
nginx), CORS isn't needed. If you see CORS errors, check that the frontend
is served through nginx (port 80), not Vite dev server.

---

## 6 — Cost Estimate

| Resource | Monthly cost | Notes |
|---|---|---|
| EC2 `t3.xlarge` | ~$40 | Running ~8h/day (on-demand model) |
| EIP | ~$3.60 | Charged while instance is stopped |
| S3 + CloudFront | ~$1 | Static frontend, low traffic |
| Lambda (wake) | ~$0 | < 1M invocations/mo |
| ECR storage | ~$1 | ~1 GB images |
| **Total** | **~$45/mo** | On-demand ~8h/day; ~$120/mo if always-on `t3.xlarge`; `t3.large` (8 GiB) is ~half but risks OOM on `deep` runs |

---

## 7 — File Map

```
├── backend/Dockerfile              # ML models baked, HF_HUB_OFFLINE=1
├── frontend/Dockerfile             # Vite build → nginx
├── docker/
│   └── nginx.conf                  # SPA + /api proxy → backend:8000
├── docker-compose.yml              # Source of truth for all services
├── .env.example                    # Template (copy to .env on the EC2)
├── .github/workflows/
│   ├── build.yml                   # Tag/dispatch → ECR push
│   └── deploy.yml                  # Dispatch → SSM compose up
├── scripts/ec2-provision.sh        # One-time EC2 bootstrap
├── infra/terraform/                # AWS infra (EC2, Lambda, S3, IAM)
└── docs/architecture/
    ├── deployment.md               # ← this file
    ├── aws-ondemand.md             # Wake/auto-stop walkthrough
    └── pipelines.md                # CI/CD details + OIDC setup
```
