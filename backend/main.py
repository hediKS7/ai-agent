import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from backend.api import auth, chat, tasks, memory, upload, followup
from backend.core.database import engine
from backend.models import Base
import backend.models.user
import backend.models.conversation

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS followups (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                agent_type VARCHAR(50) NOT NULL,
                followup_type VARCHAR(50) NOT NULL,
                context JSONB DEFAULT '{}',
                due_at TIMESTAMPTZ NOT NULL,
                triggered BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS commitments (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                description TEXT NOT NULL,
                deadline TIMESTAMPTZ NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                source_conversation_id UUID,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            ALTER TABLE conversations ADD COLUMN IF NOT EXISTS agent_type VARCHAR(50) DEFAULT 'general'
        """))
        await conn.execute(text("""
            ALTER TABLE conversations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS emotional_history (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                emotion VARCHAR(50) NOT NULL,
                intensity FLOAT DEFAULT 0.5,
                note TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weekly_summaries (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                summary_text TEXT NOT NULL,
                week_start DATE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
    yield

app = FastAPI(title="AI Agent System", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,   prefix="/auth",   tags=["Auth"])
app.include_router(chat.router,   prefix="/chat",   tags=["Chat"])
app.include_router(tasks.router,  prefix="/tasks",  tags=["Tasks"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])
app.include_router(upload.router,   prefix="/upload",   tags=["Upload"])
app.include_router(followup.router, prefix="/followups", tags=["Followups"])

@app.get("/health")
async def health():
    return {"status": "ok"}

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "out")
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Frontend dir: %s, exists: %s", frontend_dir, os.path.isdir(frontend_dir))
index_path = os.path.join(frontend_dir, "index.html")
if os.path.isfile(index_path):
    logger.info("Serving frontend from %s", frontend_dir)
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    logger.warning("Frontend build not found at %s", index_path)
