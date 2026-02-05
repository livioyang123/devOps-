# DevOps K8s Platform

An intelligent DevOps platform that transforms Docker Compose files into automated Kubernetes deployments using AI-powered conversion, with real-time monitoring and observability.

## Features

- 🚀 **AI-Powered Conversion**: Transform Docker Compose to Kubernetes manifests using LLMs
- 📁 **Drag & Drop Upload**: Easy file upload with instant validation
- ⚡ **One-Click Deployment**: Deploy to Kubernetes clusters with real-time progress
- 📊 **Real-Time Monitoring**: CPU, memory, network, and storage metrics
- 🔍 **Log Aggregation**: Centralized logging with search and filtering
- 🤖 **AI Log Analysis**: Intelligent anomaly detection and recommendations
- 🔔 **Smart Alerts**: Configurable alerts for various conditions
- 📦 **Template Library**: Pre-built templates for common application stacks
- 💰 **Cost Estimation**: Estimate cloud costs before deployment
- 🔒 **Security First**: AES-256 encryption, JWT authentication, rate limiting

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

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose
- Kubernetes cluster (local or cloud)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd devops-k8s-platform
   ```

2. **Start infrastructure services**
   ```bash
   docker-compose up -d postgres redis prometheus loki grafana
   ```

3. **Setup Backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your configuration
   uvicorn app.main:app --reload
   ```

4. **Setup Frontend**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local with your configuration
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/api/docs
   - Grafana: http://localhost:3000 (admin/admin123)
   - Prometheus: http://localhost:9090

### Using Docker Compose (Full Stack)

```bash
# Start all services
docker-compose --profile backend --profile frontend up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Usage

### 1. Upload Docker Compose
- Drag and drop your `docker-compose.yml` file
- View parsed structure (services, volumes, networks)

### 2. AI Conversion
- Configure your preferred LLM provider (OpenAI, Anthropic, etc.)
- Convert Docker Compose to Kubernetes manifests
- Review and edit generated manifests

### 3. Deploy to Kubernetes
- Select target cluster (local or cloud)
- One-click deployment with real-time progress
- Automatic rollback on failures

### 4. Monitor & Analyze
- View real-time metrics and logs
- Use AI-powered log analysis
- Configure alerts for important conditions

## Configuration

### LLM Providers

The platform supports multiple AI providers:

- **OpenAI**: GPT-4, GPT-3.5
- **Anthropic**: Claude Sonnet, Claude Opus
- **Google AI**: Gemini Pro
- **Ollama**: Local Llama models

Configure API keys in the settings page or environment variables.

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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run code quality checks
6. Submit a pull request

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