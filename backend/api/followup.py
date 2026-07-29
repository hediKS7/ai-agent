from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from agents.followup import (
    get_due_followups, mark_followup_triggered,
    get_overdue_commitments, mark_commitment_resolved,
    needs_weekly_summary, build_weekly_summary
)

router = APIRouter()

class FollowupAction(BaseModel):
    followup_id: str

class CommitAction(BaseModel):
    commitment_id: str

class SummaryRequest(BaseModel):
    user_id: str

@router.get("/{user_id}")
async def get_followups(user_id: str):
    followups = await get_due_followups(user_id)
    commitments = await get_overdue_commitments(user_id)
    return {
        "followups": followups,
        "commitments": commitments
    }

@router.post("/triggered")
async def trigger_followup(req: FollowupAction):
    await mark_followup_triggered(req.followup_id)
    return {"ok": True}

@router.post("/resolve-commitment")
async def resolve_commitment(req: CommitAction):
    await mark_commitment_resolved(req.commitment_id)
    return {"ok": True}

@router.post("/weekly-summary")
async def weekly_summary(req: SummaryRequest):
    if await needs_weekly_summary(req.user_id):
        summary = await build_weekly_summary(req.user_id)
        return {"summary": summary, "due": True}
    return {"summary": None, "due": False}
