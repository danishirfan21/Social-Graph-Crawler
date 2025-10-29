# Quick Setup & Run Guide

## For Windows (PowerShell)

### Step 1: Start Infrastructure
```powershell
# Navigate to project root
cd "d:\Social Graph Crawler\social-graph-crawler"

# Start PostgreSQL and Redis
docker-compose up -d
```

### Step 2: Setup Backend
```powershell
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Keep this terminal open!

### Step 3: Setup Frontend (New Terminal)
```powershell
# Navigate to frontend
cd "d:\Social Graph Crawler\social-graph-crawler\frontend"

# Install dependencies
npm install

# Start frontend dev server
npm start
```

### Step 4: Access Application
- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## Testing the Crawlers

### Test Reddit Crawler
```powershell
curl -X POST "http://localhost:8000/api/v1/crawl/start" `
  -H "Content-Type: application/json" `
  -d '{
    \"source\": \"reddit\",
    \"start_entity\": \"python\",
    \"depth\": 2,
    \"max_entities\": 50
  }'
```

### Test GitHub Crawler
```powershell
curl -X POST "http://localhost:8000/api/v1/crawl/start" `
  -H "Content-Type: application/json" `
  -d '{
    \"source\": \"github\",
    \"start_entity\": \"torvalds\",
    \"depth\": 2,
    \"max_entities\": 50
  }'
```

### Test Wikipedia Crawler
```powershell
curl -X POST "http://localhost:8000/api/v1/crawl/start" `
  -H "Content-Type: application/json" `
  -d '{
    \"source\": \"wikipedia\",
    \"start_entity\": \"Python_(programming_language)\",
    \"depth\": 2,
    \"max_entities\": 50
  }'
```

## Common Commands

### Check Running Containers
```powershell
docker-compose ps
```

### View Backend Logs
```powershell
docker-compose logs -f backend
```

### Stop All Services
```powershell
docker-compose down
```

### Reset Database
```powershell
docker-compose down -v
docker-compose up -d
cd backend
alembic upgrade head
```

## Troubleshooting

### Backend Won't Start
1. Check if PostgreSQL and Redis are running:
   ```powershell
   docker-compose ps
   ```

2. Check if port 8000 is available:
   ```powershell
   netstat -ano | findstr :8000
   ```

3. Check logs:
   ```powershell
   docker-compose logs postgres redis
   ```

### Frontend Won't Start
1. Delete node_modules and reinstall:
   ```powershell
   cd frontend
   Remove-Item -Recurse -Force node_modules
   npm install
   ```

2. Check if port 3000 is available:
   ```powershell
   netstat -ano | findstr :3000
   ```

### Database Connection Issues
1. Check `.env` file in project root
2. Verify DATABASE_URL format:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/social_graph
   ```

3. Test PostgreSQL connection:
   ```powershell
   docker exec -it social-graph-db psql -U postgres
   ```

## Development Workflow

### Making Changes to Backend
1. Edit Python files in `backend/app/`
2. Server auto-reloads (with `--reload` flag)
3. Test at http://localhost:8000/docs

### Making Changes to Frontend
1. Edit files in `frontend/src/`
2. React app hot-reloads automatically
3. View at http://localhost:3000

### Database Schema Changes
1. Modify models in `backend/app/models/`
2. Create migration:
   ```powershell
   cd backend
   alembic revision --autogenerate -m "Description of change"
   ```
3. Apply migration:
   ```powershell
   alembic upgrade head
   ```

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Start a Crawl**: Use the frontend at http://localhost:3000
3. **View Data**: Check nodes, edges, and graph stats
4. **Customize**: Edit crawlers, add new sources, modify UI

## Need Help?

- Check PROJECT_SUMMARY.md for detailed documentation
- Check README.md for comprehensive guide
- Review API docs at /docs endpoint
- Check logs with `docker-compose logs`

Happy crawling! 🕷️📊
