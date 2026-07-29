from fastapi import APIRouter
from pydantic import BaseModel
from agents.graphs.main_graph import agent_graph
from langchain_core.messages import HumanMessage, AIMessage
from agents.state import AgentState
from typing import Optional
from backend.core.database import AsyncSessionLocal
from sqlalchemy import text
import uuid
from datetime import datetime

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: str
    code_context: Optional[str] = None
    agent_type: Optional[str] = "general"

class NewConversationRequest(BaseModel):
    user_id: str
    agent_type: Optional[str] = "general"

async def load_conversation_history(conversation_id: str, limit: int = 10) -> list:
    """Load last N messages from a conversation for LLM context."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT role, content FROM messages
            WHERE conversation_id = :conv_id
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"conv_id": conversation_id, "limit": limit})
        rows = result.fetchall()
        # Reverse to get chronological order
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

@router.post("/conversations/new")
async def new_conversation(req: NewConversationRequest):
    conversation_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO conversations (id, user_id, title, created_at, updated_at)
            VALUES (:id, :user_id, :title, :now, :now)
        """), {
            "id": conversation_id,
            "user_id": req.user_id,
            "title": "New conversation",
            "now": datetime.utcnow()
        })
        await db.commit()
    return {"conversation_id": conversation_id}

@router.get("/conversations/{user_id}")
async def get_conversations(user_id: str, agent_type: str = "general"):
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = :user_id AND agent_type = :agent_type
            ORDER BY updated_at DESC
            LIMIT 50
        """), {"user_id": user_id, "agent_type": agent_type})
        rows = result.fetchall()
        return {"conversations": [
            {
                "id": str(r[0]),
                "title": r[1],
                "created_at": r[2].isoformat() if r[2] else None,
                "updated_at": r[3].isoformat() if r[3] else None
            }
            for r in rows
        ]}

@router.get("/conversations/{user_id}/{conversation_id}/messages")
async def get_messages(user_id: str, conversation_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT role, content, created_at, metadata
            FROM messages
            WHERE conversation_id = :conversation_id
            ORDER BY created_at ASC
        """), {"conversation_id": conversation_id})
        rows = result.fetchall()
        return {"messages": [
            {
                "role": r[0],
                "content": r[1],
                "created_at": r[2].isoformat() if r[2] else None,
                "metadata": r[3]
            }
            for r in rows
        ]}

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM messages WHERE conversation_id = :id"), {"id": conversation_id})
        await db.execute(text("DELETE FROM conversations WHERE id = :id"), {"id": conversation_id})
        await db.commit()
    return {"status": "deleted"}

@router.post("")
async def chat(req: ChatRequest):
    full_message = req.message
    if req.code_context:
        full_message = f"{req.message}\n\n```\n{req.code_context}\n```"

    # Auto-create conversation if none provided
    conversation_id = req.conversation_id
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT id FROM users WHERE id = :uid"), {"uid": req.user_id})
            if not result.scalar_one_or_none():
                await db.execute(text("""
                    INSERT INTO users (id, email, username, hashed_password, is_active, created_at)
                    VALUES (:id, :email, :username, '', TRUE, NOW())
                """), {"id": req.user_id, "email": f"{req.user_id}@auto.local", "username": req.user_id[:8]})
            await db.execute(text("""
                INSERT INTO conversations (id, user_id, title, agent_type, created_at, updated_at)
                VALUES (:id, :user_id, :title, :agent_type, :now, :now)
            """), {
                "id": conversation_id,
                "user_id": req.user_id,
                "title": req.message[:50],
                "agent_type": req.agent_type or "general",
                "now": datetime.utcnow()
            })
            await db.commit()

    # Load conversation history for LLM context
    history = await load_conversation_history(conversation_id, limit=10)

    # Build LangChain messages from history
    lc_messages = []
    for msg in history:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    # Add current message
    lc_messages.append(HumanMessage(content=full_message))

    initial_state: AgentState = {
        "messages": lc_messages,
        "conversation_history": history,
        "user_id": req.user_id,
        "task_id": "",
        "conversation_id": conversation_id,
        "intent": "",
        "agent_type": req.agent_type or "general",
        "plan": [],
        "current_step": 0,
        "tool_results": [],
        "reflection": "",
        "final_response": "",
        "needs_clarification": False,
        "clarification_question": "",
        "memory_context": "",
        "candidate_memories": [],
        "memory_actions": None,
        "sentiment": None,
        "sentiment_context": "",
        "emotional_pattern": None,
        "sustained_pattern": None
    }

    result = await agent_graph.ainvoke(initial_state)
    final_response = result["final_response"]

    # Clean up em dashes
    final_response = final_response.replace("\u2014", ",").replace("\u2013", "-")

    # Save messages to DB
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO messages (id, conversation_id, role, content, created_at)
            VALUES (:id, :conv_id, 'user', :content, :now)
        """), {"id": str(uuid.uuid4()), "conv_id": conversation_id,
               "content": req.message, "now": datetime.utcnow()})

        await db.execute(text("""
            INSERT INTO messages (id, conversation_id, role, content, metadata, created_at)
            VALUES (:id, :conv_id, 'assistant', :content, :meta, :now)
        """), {"id": str(uuid.uuid4()), "conv_id": conversation_id,
               "content": final_response,
               "meta": f'{{"agent_type": "{req.agent_type}"}}',
               "now": datetime.utcnow()})

        await db.execute(text("""
            UPDATE conversations
            SET updated_at = :now,
                title = CASE WHEN title = 'New conversation' THEN :title ELSE title END
            WHERE id = :id
        """), {"id": conversation_id, "title": req.message[:50], "now": datetime.utcnow()})
        await db.commit()

    return {
        "response": final_response,
        "intent": result["intent"],
        "agent_type": result["agent_type"],
        "conversation_id": conversation_id,
        "plan": result["plan"],
    }
