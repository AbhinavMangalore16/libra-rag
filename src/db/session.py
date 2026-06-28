from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.core.config import get_settings

settings = get_settings()

if not settings.POSTGRES_DATABASE_URL:
    raise ValueError("POSTGRES_DATABASE_URL must be set for database operations")

# Create Async Engine for Neon Postgres
db_url = settings.POSTGRES_DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# asyncpg uses `ssl` instead of `sslmode`
if "sslmode=" in db_url:
    db_url = db_url.replace("sslmode=", "ssl=")
if "channel_binding=require" in db_url:
    # asyncpg doesn't support channel_binding in URL this way
    db_url = db_url.replace("&channel_binding=require", "").replace("?channel_binding=require", "")

engine = create_async_engine(
    db_url, 
    echo=False, 
    # Neon postgres pooling compatibility
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def init_db():
    from src.db.models import Base
    async with engine.begin() as conn:
        # Warning: create_all is fine for MVP, use Alembic for prod!
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
