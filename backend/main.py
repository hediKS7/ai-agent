from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import auth, chat, tasks, memory, upload, followup
from backend.core.database import engine
from backend.models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
