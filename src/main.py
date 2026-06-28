from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import get_settings

settings = get_settings()

from contextlib import asynccontextmanager
from langchain_core.globals import set_llm_cache
from langchain_community.cache import RedisCache
import redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
        print("Initializing Standard Redis Cache for ChatModels...")
        # Construct the TCP URL from the REST URL and Token
        host = settings.UPSTASH_REDIS_REST_URL.replace("https://", "")
        password = settings.UPSTASH_REDIS_REST_TOKEN
        redis_url = f"rediss://default:{password}@{host}:6379"
        
        redis_client = redis.Redis.from_url(redis_url)
        set_llm_cache(RedisCache(redis_=redis_client))
        
    if settings.POSTGRES_DATABASE_URL:
        print("Initializing Neon Postgres Database...")
        from src.db.session import init_db
        await init_db()
        
    yield

import logfire
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic RAG API Backend",
    lifespan=lifespan,
)

logfire.instrument_fastapi(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION}

from fastapi.responses import HTMLResponse
from src.api.routers import ingest, search, agent

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
        <head>
            <title>Agentic RAG - Backend Dashboard</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 40px; display: flex; flex-direction: column; align-items: center; }
                h1 { color: #38bdf8; margin-bottom: 10px; }
                p { color: #94a3b8; margin-bottom: 40px; text-align: center; max-width: 600px; }
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; width: 100%; max-width: 900px; }
                .card { background-color: #1e293b; border-radius: 12px; padding: 24px; text-align: center; text-decoration: none; color: white; transition: all 0.3s ease; border: 1px solid #334155; display: flex; flex-direction: column; justify-content: center; min-height: 120px; }
                .card:hover { transform: translateY(-5px); border-color: #38bdf8; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); }
                .card h3 { margin: 0 0 10px 0; color: #f8fafc; font-size: 1.2rem; }
                .card p { margin: 0; color: #94a3b8; font-size: 0.9rem; }
                .badge { display: inline-block; padding: 4px 8px; border-radius: 9999px; font-size: 0.7rem; font-weight: bold; margin-bottom: 15px; }
                .fastapi { background: #047857; color: #d1fae5; }
                .airflow { background: #be185d; color: #fce7f3; }
                .opensearch { background: #0369a1; color: #e0f2fe; }
                .logfire { background: #b45309; color: #fef3c7; }
                .locust { background: #4338ca; color: #e0e7ff; }
            </style>
        </head>
        <body>
            <h1>🚀 Backend Control Center</h1>
            <p>Welcome to your centralized dashboard. Click on any card below to jump directly to the specific service or dashboard.</p>
            
            <div class="grid">
                <a href="/docs" target="_blank" class="card">
                    <div><span class="badge fastapi">FastAPI</span></div>
                    <h3>Swagger UI</h3>
                    <p>Test your API endpoints interactively</p>
                </a>
                
                <a href="http://localhost:8080" target="_blank" class="card">
                    <div><span class="badge airflow">Airflow</span></div>
                    <h3>Task Orchestrator</h3>
                    <p>Monitor ingestion pipelines (admin/admin)</p>
                </a>
                
                <a href="http://localhost:5601" target="_blank" class="card">
                    <div><span class="badge opensearch">OpenSearch</span></div>
                    <h3>Vector DB Dashboards</h3>
                    <p>Visualize and manage vector indexes</p>
                </a>
                
                <a href="https://logfire.pydantic.dev/" target="_blank" class="card">
                    <div><span class="badge logfire">Logfire</span></div>
                    <h3>Observability</h3>
                    <p>View Pydantic & FastAPI telemetry logs</p>
                </a>
                
                <a href="http://localhost:8089" target="_blank" class="card">
                    <div><span class="badge locust">Locust</span></div>
                    <h3>Load Testing</h3>
                    <p>Simulate concurrent user traffic</p>
                </a>
            </div>
        </body>
    </html>
    """

app.include_router(ingest.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(agent.router, prefix=settings.API_V1_STR)
