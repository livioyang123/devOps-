# DevOps K8s Platform

An intelligent DevOps platform that transforms Docker Compose files into automated Kubernetes deployments using AI-powered conversion, with real-time monitoring and observability.

## 🌟 Features

- 🚀 **AI-Powered Conversion**: Transform Docker Compose to Kubernetes manifests using LLMs (GPT-4, Claude, Gemini, Llama)
- 📁 **Drag & Drop Upload**: Easy file upload with instant YAML validation and structure preview
- ⚡ **One-Click Deployment**: Deploy to Kubernetes clusters with real-time WebSocket progress updates
- 📊 **Real-Time Monitoring**: CPU, memory, network, and storage metrics with Prometheus integration
- 🔍 **Log Aggregation**: Centralized logging with Loki, full-text search, and filtering
- 🤖 **AI Log Analysis**: Intelligent anomaly detection, error identification, and actionable recommendations
- 🔔 **Smart Alerts**: Configurable alerts for CPU/memory thresholds, pod restarts, and deployment failures
- 📦 **Template Library**: Pre-built templates for WordPress, LAMP, MEAN, PostgreSQL+Redis
- 💰 **Cost Estimation**: Estimate GKE/EKS/AKS costs before deployment
- 🔒 **Security First**: AES-256 encryption, JWT authentication, rate limiting, input sanitization, RBAC
- 🌙 **Dark Mode**: Full dark mode support across all components
- 📤 **Manifest Export**: Download generated manifests as organized ZIP archives

## Architecture

### Frontend (Next.js 14+)
- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript
- **Styling**: TailwindCSS + shadcn/ui
- **State Management**: React Query
- **Code Editor**: Monaco Editor
- **Charts**: Recharts
- **WebSocket**: Real-time updates

### Backend (FastAPI)
- **Framework**: FastAPI with Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy
- **Cache**: Redis
- **Task Queue**: Celery
- **Authentication**: JWT
- **Monitoring**: Prometheus + Loki
- **AI Integration**: Multiple LLM providers (OpenAI, Anthropic, Google, Ollama)

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Orchestration**: Kubernetes
- **Monitoring**: Prometheus, Loki, Grafana
- **Development**: Local cluster support (minikube, kind)
- **Production**: Cloud support (GKE, EKS, AKS)

## 🚀 Quick Start

### Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** 18+ and npm
- **Python** 3.11+
- **Docker** 20.10+ and Docker Compose 2.0+
- **Kubernetes cluster** (one of):
  - Local: [minikube](https://minikube.sigs.k8s.io/) or [kind](https://kind.sigs.k8s.io/)
  - Cloud: GKE, EKS, or AKS with kubectl configured
- **AI Provider API Key** (at least one):
  - [OpenAI API Key](https://platform.openai.com/api-keys)
  - [Anthropic API Key](https://console.anthropic.com/)
  - [Google AI API Key](https://makersuite.google.com/app/apikey)
  - Or [Ollama](https://ollama.ai/) for local models

### Option 1: Docker Compose (Recommended for Quick Start)

The fastest way to get started is using Docker Compose to run the entire stack:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/devops-k8s-platform.git
cd devops-k8s-platform

# 2. Start all services (frontend, backend, database, monitoring)
docker-compose up -d

# 3. Wait for services to be ready (about 30-60 seconds)
docker-compose ps

# 4. Check health status
curl http://localhost:8000/health/detailed

# 5. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
# Grafana: http://localhost:3001 (admin/admin123)
# Prometheus: http://localhost:9090
```

**First-time setup**:
1. Open http://localhost:3000
2. Navigate to Configuration
3. Add your AI provider API key
4. Navigate to Clusters
5. Add your Kubernetes cluster
6. Start converting and deploying!

### Option 2: Local Development Setup

For active development with hot-reload:

#### Step 1: Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/your-org/devops-k8s-platform.git
cd devops-k8s-platform
```

#### Step 2: Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, Prometheus, Loki, Grafana
docker-compose up -d postgres redis prometheus loki grafana

# Verify services are running
docker-compose ps
```

#### Step 3: Setup Backend

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env

# Edit .env with your configuration (see Environment Variables section below)
# Required: DATABASE_URL, REDIS_URL, SECRET_KEY, at least one LLM API key

# Run database migrations
alembic upgrade head

# Seed template data (optional)
python seed_templates.py

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or start Celery worker in another terminal
celery -A app.celery_app worker --loglevel=info
```

#### Step 4: Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Setup environment variables
cp .env.example .env.local

# Edit .env.local with your configuration
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Start the development server
npm run dev
```

#### Step 5: Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Grafana**: http://localhost:3001 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Loki**: http://localhost:3100

### Option 3: Production Deployment

See the [Production Deployment](#production-deployment) section below for detailed instructions.

## 📖 Usage

### Complete Workflow Example

#### 1. Upload Docker Compose File

Navigate to http://localhost:3000 and:
- Drag and drop your `docker-compose.yml` file into the upload zone
- Or click to browse and select your file
- The platform validates YAML syntax automatically
- View the parsed structure showing services, volumes, and networks

**Example Docker Compose**:
```yaml
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    environment:
      - NGINX_HOST=example.com
    volumes:
      - ./html:/usr/share/nginx/html
  
  db:
    image: postgres:14
    environment:
      - POSTGRES_PASSWORD=secret
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:
```

#### 2. AI-Powered Conversion

- Click "Convert to Kubernetes"
- The AI processes your Docker Compose file (5-15 seconds)
- Generated manifests include:
  - Deployments for each service
  - Services for network exposure
  - ConfigMaps for environment variables
  - Secrets for sensitive data
  - PersistentVolumeClaims for volumes
  - Health checks and resource limits
  - Security contexts and best practices

#### 3. Review and Edit Manifests

- View all generated Kubernetes YAML files in the Manifest Editor
- Use the Diff View to compare Docker Compose with Kubernetes manifests
- Edit any manifest directly with syntax highlighting
- Real-time YAML validation catches errors as you type
- Export manifests as ZIP for version control

#### 4. Deploy to Kubernetes

- Select your target cluster from the dropdown
- Review cost estimate (for cloud clusters)
- Click "Deploy"
- Watch real-time progress via WebSocket:
  - Progress bar shows overall completion
  - Status updates for each manifest
  - Current step and estimated time remaining
- Automatic health checks verify pod status
- Automatic rollback on any failures

#### 5. Monitor and Analyze

**Real-Time Metrics**:
- CPU usage per pod
- Memory usage per pod
- Network traffic (RX/TX)
- Storage usage
- Interactive charts with time range selection

**Log Viewing**:
- Real-time log streaming from all pods
- Full-text search across logs
- Filter by pod, time range, or log level
- Color-coded by severity

**AI Log Analysis**:
- Click "Analyze Logs"
- AI detects anomalies and common errors
- Get actionable recommendations
- Identify OOMKilled, CrashLoopBackOff, ImagePullBackOff

#### 6. Configure Alerts

- Navigate to Alerts
- Create alerts for:
  - CPU threshold exceeded
  - Memory threshold exceeded
  - Pod restart count
  - Deployment failures
- Choose notification channel (email, webhook, in-app)
- Receive notifications when conditions are met

### Using Templates

Quick-start with pre-built templates:

1. Navigate to Templates
2. Browse available templates:
   - WordPress (WordPress + MySQL)
   - LAMP Stack (Linux, Apache, MySQL, PHP)
   - MEAN Stack (MongoDB, Express, Angular, Node.js)
   - PostgreSQL + Redis
3. Click "Use Template"
4. Fill in required parameters
5. Proceed with normal conversion workflow

### API Usage

You can also use the platform programmatically via the REST API:

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "password"}'

# Parse Docker Compose
curl -X POST http://localhost:8000/api/compose/parse \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "version: \"3.8\"\nservices:\n  web:\n    image: nginx:latest"}'

# Convert to Kubernetes
curl -X POST http://localhost:8000/api/convert \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"compose_content": "...", "model": "gpt-4"}'

# Deploy
curl -X POST http://localhost:8000/api/deploy \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"manifests": [...], "cluster_id": "..."}'
```

See [API Documentation](backend/docs/API_DOCUMENTATION.md) for complete API reference.

## Environment Variables

### Backend (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `REDIS_URL` | Yes | — | Redis connection string (cache) |
| `CELERY_BROKER_URL` | Yes | — | Redis URL for Celery broker |
| `CELERY_RESULT_BACKEND` | Yes | — | Redis URL for Celery results |
| `SECRET_KEY` | Yes | — | JWT signing secret (use a strong random value in production) |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT token expiry |
| `ENCRYPTION_KEY` | Yes | — | AES-256 key for encrypting API keys (must be 32 chars) |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | API rate limit per client |
| `PROMETHEUS_URL` | No | `http://localhost:9090` | Prometheus endpoint |
| `LOKI_URL` | No | `http://localhost:3100` | Loki log aggregation endpoint |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `DEBUG` | No | `true` | Enable debug logging |

### Frontend (`frontend/.env.local`)

Copy `frontend/.env.example` to `frontend/.env.local` and configure:

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | Backend API base URL |
| `NEXT_PUBLIC_WS_URL` | No | `ws://localhost:8000` | WebSocket base URL |
| `NEXT_PUBLIC_APP_NAME` | No | `DevOps K8s Platform` | Application display name |
| `NEXT_PUBLIC_APP_VERSION` | No | `1.0.0` | Application version |

## Configuration

### LLM Providers

The platform supports multiple AI providers:

- **OpenAI**: GPT-4, GPT-3.5
- **Anthropic**: Claude Sonnet, Claude Opus
- **Google AI**: Gemini Pro
- **Ollama**: Local Llama models (no API key required)

Configure API keys in the settings page or via environment variables.

### Kubernetes Clusters

Supported cluster types:
- **Local**: minikube, kind
- **Cloud**: GKE, EKS, AKS

Add clusters through the configuration interface.

## Development

### Project Structure

```
├── frontend/          # Next.js frontend application
│   ├── src/
│   │   ├── app/       # App Router pages
│   │   ├── components/ # React components
│   │   └── lib/       # Utilities
├── backend/           # FastAPI backend application
│   ├── app/
│   │   ├── routers/   # API routes
│   │   ├── services/  # Business logic
│   │   ├── models/    # Database models
│   │   └── utils/     # Utilities
├── infra/             # Infrastructure configuration
│   ├── prometheus/    # Prometheus config
│   ├── loki/         # Loki config
│   └── grafana/      # Grafana config
└── docker-compose.yml # Development environment
```

### Code Quality

**Frontend**:
```bash
npm run lint          # ESLint
npm run format        # Prettier
npm run type-check    # TypeScript
```

**Backend**:
```bash
black .               # Code formatting
mypy .                # Type checking
pytest                # Run tests
```

### Testing

The project uses both unit tests and property-based tests:

**Frontend**: Jest + React Testing Library + fast-check
**Backend**: pytest + Hypothesis

```bash
# Frontend tests
cd frontend && npm test

# Backend tests
cd backend && pytest
```

## Production Deployment

### Prerequisites

- A Kubernetes cluster (GKE, EKS, AKS, or self-managed)
- `kubectl` configured with cluster access
- A container registry (Docker Hub, GCR, ECR, etc.)
- PostgreSQL and Redis instances (managed services recommended)

### 1. Build and Push Images

```bash
# Backend
docker build -t your-registry/devops-k8s-backend:latest ./backend
docker push your-registry/devops-k8s-backend:latest

# Frontend
docker build -t your-registry/devops-k8s-frontend:latest ./frontend
docker push your-registry/devops-k8s-frontend:latest
```

### 2. Configure Secrets

Create Kubernetes secrets for sensitive values:

```bash
kubectl create secret generic devops-k8s-secrets \
  --from-literal=DATABASE_URL="postgresql://user:pass@host:5432/db" \
  --from-literal=REDIS_URL="redis://host:6379/0" \
  --from-literal=SECRET_KEY="your-strong-secret-key" \
  --from-literal=ENCRYPTION_KEY="your-32-char-encryption-key"
```

### 3. Apply RBAC

Apply the RBAC configuration for the platform's service account:

```bash
kubectl apply -f backend/k8s/rbac/service-account.yaml
kubectl apply -f backend/k8s/rbac/deployer-role.yaml
kubectl apply -f backend/k8s/rbac/monitor-role.yaml
kubectl apply -f backend/k8s/rbac/role-bindings.yaml
```

See [backend/k8s/rbac/README.md](backend/k8s/rbac/README.md) for details.

### 4. Deploy Backend

```bash
# Create a deployment manifest referencing your image and secrets
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
```

### 5. Run Database Migrations

```bash
kubectl exec -it <backend-pod> -- alembic upgrade head
kubectl exec -it <backend-pod> -- python seed_templates.py
```

### 6. Deploy Frontend

```bash
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/ingress.yaml
```

### 7. Configure Monitoring

Deploy Prometheus and Loki to your cluster, or use managed alternatives (Google Cloud Monitoring, AWS CloudWatch, etc.). Update `PROMETHEUS_URL` and `LOKI_URL` environment variables accordingly.

### Production Checklist

- [ ] Use strong, randomly generated `SECRET_KEY` and `ENCRYPTION_KEY`
- [ ] Set `ENVIRONMENT=production` and `DEBUG=false`
- [ ] Use managed PostgreSQL and Redis (not in-cluster for production)
- [ ] Configure TLS/HTTPS via Ingress with cert-manager
- [ ] Set resource requests and limits on all pods
- [ ] Enable horizontal pod autoscaling
- [ ] Configure log retention policies
- [ ] Set up backup for PostgreSQL
- [ ] Rotate API keys and secrets regularly

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes following the code style guidelines
4. Add tests for new functionality
5. Run code quality checks:
   ```bash
   # Backend
   cd backend && black . && mypy . && pytest

   # Frontend
   cd frontend && npm run lint && npm run type-check && npm test
   ```
6. Submit a pull request with a clear description of changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Documentation

### Project Documentation
- 📖 [Documentation Index](docs/README.md)
- � [File Organization Guide](docs/FILE_ORGANIZATION.md)
- 🔧 [Infrastructure Verification](docs/INFRASTRUCTURE_VERIFICATION.md)

### Backend Documentation
- � [Backend API Documentation](backend/docs/README.md)
- 🔄 [Conversion API Guide](backend/docs/CONVERSION_API_IMPLEMENTATION.md)
- 🤖 [LLM Router Implementation](backend/docs/LLM_ROUTER_IMPLEMENTATION.md)
- 🔐 [Authentication & Security](backend/docs/AUTHENTICATION_SECURITY_IMPLEMENTATION.md)

### Testing
- 🧪 [Backend Tests](backend/tests/README.md)
- ✅ [Running Tests](backend/tests/README.md#running-tests)

## Support

- 📖 [Full Documentation](docs/)
- 🐛 [Issue Tracker](issues/)
- 💬 [Discussions](discussions/)

## Roadmap

- [ ] Multi-tenancy support
- [ ] GitOps integration
- [ ] Advanced RBAC
- [ ] Custom resource definitions
- [ ] Helm chart support
- [ ] CI/CD pipeline integration