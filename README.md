# FileSystem

A browser-based virtual file system built with FastAPI and React.

## Run With Docker

```bash
docker compose up --build
```

http://localhost

## Run Without Docker

```bash
# backend
cd backend && pip install uv && uv pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend && npm install && npm run dev
```

http://localhost:5173