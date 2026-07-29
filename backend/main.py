import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

        # ── Extensions ──────────────────────────────────────────────
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass

        # ── CREATE all tables (IF NOT EXISTS so safe to re-run) ────
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS followups (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                description TEXT NOT NULL,
                deadline TIMESTAMPTZ NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                source_conversation_id UUID,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS emotional_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                emotion VARCHAR(50) NOT NULL,
                intensity FLOAT DEFAULT 0.5,
                note TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weekly_summaries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                summary_text TEXT NOT NULL,
                week_start DATE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                conversation_id UUID REFERENCES conversations(id),
                title TEXT NOT NULL,
                description TEXT,
                status VARCHAR(30) DEFAULT 'pending',
                plan JSONB,
                result JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                task_id UUID REFERENCES tasks(id),
                message_id UUID REFERENCES messages(id),
                tool_name VARCHAR(100) NOT NULL,
                input JSONB,
                output JSONB,
                status VARCHAR(20) DEFAULT 'success',
                duration_ms INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                task_id UUID REFERENCES tasks(id),
                agent_name VARCHAR(100),
                event_type VARCHAR(50),
                data JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    summary TEXT,
                    memory_type VARCHAR(50) DEFAULT 'episodic',
                    importance_score FLOAT DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            """))
        except Exception:
            pass  # pgvector not installed

        # ── Memory subsystem tables (from memory/vector/store.py) ──────
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id UUID PRIMARY KEY,
                profile JSONB NOT NULL DEFAULT '{}',
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS consolidation_log (
                user_id UUID PRIMARY KEY,
                chats_since_last INTEGER DEFAULT 0,
                last_consolidated TIMESTAMPTZ,
                summary TEXT
            )
        """))
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS episodic_memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(1024),
                    event_type VARCHAR(50) DEFAULT 'chat',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS semantic_memories (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(1024),
                    category VARCHAR(50) DEFAULT 'fact',
                    version INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT TRUE,
                    importance_score FLOAT DEFAULT 0.5,
                    frequency INTEGER DEFAULT 0,
                    last_accessed TIMESTAMPTZ,
                    superseded_by UUID,
                    content_tsv tsvector,
                    archived BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
        except Exception:
            pass  # pgvector not installed — memories/semantic/episodic tables unavailable

        # ── ALTER existing tables (fix columns missing from old deploys) ──
        await conn.execute(text("""
            ALTER TABLE messages ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'
        """))
        await conn.execute(text("""
            ALTER TABLE commitments ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending'
        """))
        await conn.execute(text("""
            ALTER TABLE conversations ADD COLUMN IF NOT EXISTS agent_type VARCHAR(50) DEFAULT 'general'
        """))
        await conn.execute(text("""
            ALTER TABLE conversations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()
        """))
        await conn.execute(text("""
            ALTER TABLE emotional_history ALTER COLUMN id SET DEFAULT gen_random_uuid()
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
