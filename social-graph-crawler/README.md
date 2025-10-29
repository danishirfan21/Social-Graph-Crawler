# Social Graph Crawler & Network Mapper

A production-ready system for crawling, storing, and visualizing social network relationships from public APIs (Reddit, GitHub, Wikipedia).

![Project Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🎯 Features

- **Multi-Source Crawling**: Reddit, GitHub, Wikipedia data collection
- **Async Architecture**: High-performance concurrent data fetching
- **Graph Database**: PostgreSQL with efficient graph queries
- **RESTful API**: Comprehensive FastAPI endpoints
- **Interactive Visualization**: D3.js force-directed graph rendering
- **Rate Limiting**: Redis-backed intelligent rate control
- **Background Jobs**: Async crawler execution
- **Testing Suite**: Pytest with >80% coverage goal

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   React     │────▶│   FastAPI   │────▶│ PostgreSQL  │
│   + D3.js   │     │   + Redis   │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Crawlers   │
                    │ Reddit/GH   │
                    └─────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for frontend)
- Git

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/social-graph-crawler.git
cd social-graph-crawler
```

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API credentials (optional for Reddit public API)
nano .env
```

### 3. Start Services with Docker

```bash
# Start all services (PostgreSQL, Redis, Backend)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend
```

The API will be available at: http://localhost:8000

### 4. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Access API documentation
open http://localhost:8000/docs
```

## 🛠️ Local Development Setup

### Backend Setup (Without Docker)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (using Docker)
docker-compose up postgres redis -d

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Management

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Access pgAdmin (optional)
docker-compose --profile tools up pgadmin
# Open http://localhost:5050 (admin@admin.com / admin)
```

## 📖 API Usage Examples

### Start a Crawl Job

```bash
curl -X POST "http://localhost:8000/api/v1/crawl/start" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "start_entity": "python",
    "depth": 2,
    "max_entities": 100
  }'
```

### Query Graph

```bash
curl -X POST "http://localhost:8000/api/v1/graph/query" \
  -H "Content-Type: application/json" \
  -d '{
    "start_node_id": "uuid-here",
    "depth": 2,
    "max_nodes": 100,
    "direction": "both"
  }'
```

### Get Graph Statistics

```bash
curl "http://localhost:8000/api/v1/graph/stats"
```

### Search Nodes

```bash
curl "http://localhost:8000/api/v1/nodes/search/?q=python&limit=20"
```

## 🧪 Testing

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_nodes.py

# View coverage report
open htmlcov/index.html
```

### Writing Tests

```python
# tests/test_api/test_nodes.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_node():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/nodes/", json={
            "entity_type": "user",
            "entity_id": "test_user",
            "source": "reddit",
            "display_name": "Test User"
        })
        assert response.status_code == 201
```

## 📊 Data Model

### Node (Entity)
```python
{
    "id": "uuid",
    "entity_type": "user|repo|subreddit|page",
    "entity_id": "external_id",
    "source": "reddit|github|wikipedia",
    "display_name": "Human readable name",
    "metadata": {
        "subscribers": 1000000,
        "karma": 5000,
        ...
    }
}
```

### Edge (Relationship)
```python
{
    "id": "uuid",
    "source_node_id": "uuid",
    "target_node_id": "uuid",
    "relationship_type": "follows|contributes|links_to",
    "weight": 0.75,
    "metadata": {
        "interaction_count": 42,
        ...
    }
}
```

## 🎨 Frontend Development

### Setup Frontend (Coming Soon)

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### D3.js Graph Visualization

```javascript
// Example graph visualization setup
import * as d3 from 'd3';

const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(edges).id(d => d.id))
  .force("charge", d3.forceManyBody().strength(-100))
  .force("center", d3.forceCenter(width / 2, height / 2));
```

## 🚢 Deployment

### Deploy to Render

1. **Create Web Service**:
   - Repository: Link your GitHub repo
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

2. **Add PostgreSQL Database**:
   - Create PostgreSQL instance
   - Copy connection string to `DATABASE_URL`

3. **Add Redis Instance**:
   - Create Redis instance
   - Copy connection string to `REDIS_URL`

### Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

### Environment Variables for Production

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
CORS_ORIGINS=["https://your-frontend.vercel.app"]
DEBUG=false
LOG_LEVEL=INFO
GITHUB_TOKEN=your_github_token
```

## 🔧 Configuration

### Crawler Settings

Edit `app/config.py` to adjust:

```python
# Maximum crawl depth
MAX_CRAWL_DEPTH = 3

# Maximum nodes per job
MAX_NODES_PER_JOB = 1000

# Concurrent requests
CRAWLER_CONCURRENCY = 10

# Rate limiting (requests per second)
RATE_LIMIT = 1.0  # For Reddit
```

### Database Performance

```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_nodes_display_name_trgm 
ON nodes USING gin(display_name gin_trgm_ops);

-- Enable query statistics
ALTER SYSTEM SET track_activities = on;
ALTER SYSTEM SET track_counts = on;
```

## 📈 Performance Optimization

### Database
- Connection pooling (20 connections by default)
- Prepared statements
- Recursive CTE for graph traversal
- GIN indexes on JSONB columns

### API
- Redis caching (1 hour TTL)
- Background job processing
- Async/await throughout
- Response compression

### Crawler
- Rate limiting per source
- Exponential backoff on errors
- Concurrent fetching (10 workers)
- Request deduplication

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error**:
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart service
docker-compose restart postgres
```

**Redis Connection Error**:
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping
# Should return: PONG
```

**Import Errors**:
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📚 API Documentation

Full API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/nodes/` | GET | List nodes |
| `/api/v1/nodes/` | POST | Create node |
| `/api/v1/edges/` | GET | List edges |
| `/api/v1/graph/query` | POST | Query subgraph |
| `/api/v1/graph/stats` | GET | Graph statistics |
| `/api/v1/crawl/start` | POST | Start crawl job |
| `/api/v1/crawl/jobs` | GET | List crawl jobs |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Use type hints
- Write meaningful commit messages

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [D3.js Network Graphs](https://observablehq.com/@d3/force-directed-graph)
- [Graph Theory Basics](https://en.wikipedia.org/wiki/Graph_theory)

## 🌟 Showcase

Perfect for demonstrating:
- Async Python programming
- RESTful API design
- Graph database modeling
- Data visualization
- Docker containerization
- Testing best practices

## 📧 Contact

Your Name - [@yourtwitter](https://twitter.com/yourtwitter)

Project Link: [https://github.com/yourusername/social-graph-crawler](https://github.com/yourusername/social-graph-crawler)

---

Made with ❤️ for the developer community