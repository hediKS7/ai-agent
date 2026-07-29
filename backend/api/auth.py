from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from backend.core.database import AsyncSessionLocal
from backend.core.security import hash_password, verify_password, create_access_token
from backend.models.user import User
from sqlalchemy import text
from sqlalchemy import select
import uuid

router = APIRouter()
security = HTTPBearer()

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    email: str

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    from jose import jwt, JWTError
    from backend.core.config import settings
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where((User.email == req.email) | (User.username == req.username))
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email or username already exists")

        user_id = str(uuid.uuid4())
        hashed = hash_password(req.password)
        await db.execute(text("""
            INSERT INTO users (id, email, username, hashed_password, is_active, created_at)
            VALUES (:id, :email, :username, :password, TRUE, NOW())
        """), {"id": user_id, "email": req.email, "username": req.username, "password": hashed})
        await db.commit()

    token = create_access_token({"sub": user_id, "username": req.username})
    return AuthResponse(access_token=token, user_id=user_id, username=req.username, email=req.email)

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == req.username)
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": str(user.id), "username": user.username})
    return AuthResponse(access_token=token, user_id=str(user.id), username=user.username, email=user.email)

@router.get("/me")
async def get_me(user_id: str = Depends(get_current_user)):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"user_id": str(user.id), "username": user.username, "email": user.email}