from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from .. import models
from ..db import get_db
from ..auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token, 
    get_current_active_user, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(tags=["users"])

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

class DashboardData(BaseModel):
    websites_count: int
    redirects_count: int
    github_mappings_count: int
    max_allowed: int = 2

@router.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if username already exists
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )
    
    # Check if email already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user with hashed password
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {
        "id": db_user.id,
        "username": db_user.username,
        "email": db_user.email
    }

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login to get access token"""
    
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_user_profile(current_user: models.User = Depends(get_current_active_user)):
    """Get current user profile"""
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }

@router.get("/dashboard")
async def get_dashboard_data(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard data with user's resource counts"""
    
    # Count user's resources
    websites_count = db.query(models.Website).filter(models.Website.user_id == current_user.id).count()
    redirects_count = db.query(models.Redirect).filter(models.Redirect.user_id == current_user.id).count()
    github_mappings_count = db.query(models.GitHubMapping).filter(models.GitHubMapping.user_id == current_user.id).count()
    
    # Get all user's resources
    websites = db.query(models.Website).filter(models.Website.user_id == current_user.id).all()
    redirects = db.query(models.Redirect).filter(models.Redirect.user_id == current_user.id).all()
    github_mappings = db.query(models.GitHubMapping).filter(models.GitHubMapping.user_id == current_user.id).all()
    
    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
        },
        "resource_counts": {
            "websites": websites_count,
            "redirects": redirects_count,
            "github_mappings": github_mappings_count,
            "max_allowed": 2
        },
        "websites": websites,
        "redirects": redirects,
        "github_mappings": github_mappings
    }