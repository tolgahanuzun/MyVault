from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import timedelta
from backend.database import get_db
from backend.models import User
from backend.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
import shutil
import os
from pathlib import Path
import uuid

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str | None = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str

class UserRead(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    avatar_url: str | None = None
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: str | None = None

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

import re

def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True

@router.post("/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Validate password complexity
    if not validate_password(user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase letters and numbers."
        )

    # Check if user already exists
    result = await db.execute(select(User).filter(User.username == user.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        full_name=user.full_name,
        hash_password=hashed_password,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": new_user.id,
        "username": new_user.username
    }

@router.post("/login", response_model=Token)
async def login_for_access_token(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    # Find user
    result = await db.execute(select(User).filter(User.username == user_data.username))
    user = result.scalars().first()
    
    if not user or not user.hash_password or not verify_password(user_data.password, user.hash_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username
    }

@router.get("/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserRead)
async def update_user_me(user_update: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Create uploads directory if not exists
    upload_dir = Path("frontend/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / filename
    
    # Save file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Update user avatar_url
    # Store relative path for frontend access
    relative_path = f"/static/uploads/{filename}"
    current_user.avatar_url = relative_path
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return current_user

@router.post("/me/password")
async def change_password(password_update: UserPasswordUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not verify_password(password_update.current_password, current_user.hash_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    hashed_password = get_password_hash(password_update.new_password)
    current_user.hash_password = hashed_password
    
    db.add(current_user)
    await db.commit()
    
    return {"message": "Password updated successfully"}
