import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from .. import models
from ..db import get_db
from ..auth import get_current_active_user
from ..utils import cloudflare, validators

router = APIRouter(tags=["github-pages"])

class GitHubMappingCreate(BaseModel):
    subdomain: str
    github_username: str
    repository_name: str

class GitHubMappingUpdate(BaseModel):
    subdomain: str
    github_username: str
    repository_name: str

@router.get("/github-mappings", response_model=List)
async def get_user_github_mappings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all GitHub mappings created by the current user"""
    mappings = db.query(models.GitHubMapping).filter(models.GitHubMapping.user_id == current_user.id).all()
    return mappings

@router.get("/github-mapping/count")
async def get_github_mapping_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get the count of GitHub mappings created by the current user"""
    count = db.query(func.count(models.GitHubMapping.id)).filter(
        models.GitHubMapping.user_id == current_user.id
    ).scalar()
    
    return {"count": count}

@router.post("/map-github", status_code=status.HTTP_201_CREATED)
async def create_github_mapping(
    mapping: GitHubMappingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new GitHub Pages mapping"""
    
    # Check if user has reached their limit of 2 mappings
    mapping_count = db.query(func.count(models.GitHubMapping.id)).filter(
        models.GitHubMapping.user_id == current_user.id
    ).scalar()
    
    if mapping_count >= 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have reached the limit of 2 GitHub mappings. Contact admin to add more."
        )
    
    # Validate subdomain
    is_valid_subdomain, subdomain_error = validators.validate_subdomain(mapping.subdomain)
    if not is_valid_subdomain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=subdomain_error
        )
    
    # Validate GitHub username
    is_valid_username, username_error = validators.validate_github_username(mapping.github_username)
    if not is_valid_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=username_error
        )
    
    # Validate repository name
    is_valid_repo, repo_error = validators.validate_repository_name(mapping.repository_name)
    if not is_valid_repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=repo_error
        )
    
    # Check if subdomain already exists
    existing = db.query(models.GitHubMapping).filter(models.GitHubMapping.subdomain == mapping.subdomain).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This subdomain is already in use"
        )
    
    # Create CNAME record in Cloudflare
    cf_result = cloudflare.create_github_pages_mapping(mapping.subdomain, mapping.github_username)
    
    if not cf_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set up DNS: {cf_result['error']}"
        )
    
    # Save to database
    new_mapping = models.GitHubMapping(
        subdomain=mapping.subdomain,
        github_username=mapping.github_username,
        repository_name=mapping.repository_name,
        user_id=current_user.id
    )
    
    db.add(new_mapping)
    db.commit()
    db.refresh(new_mapping)
    
    domain_name = os.getenv("DOMAIN_NAME", "sriox.com")
    
    return {
        "id": new_mapping.id,
        "subdomain": new_mapping.subdomain,
        "github_username": new_mapping.github_username,
        "repository_name": new_mapping.repository_name,
        "created_at": new_mapping.created_at,
        "url": f"https://{mapping.subdomain}.{domain_name}"
    }

@router.put("/map-github/{mapping_id}")
async def update_github_mapping(
    mapping_id: int,
    mapping_update: GitHubMappingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update a GitHub Pages mapping"""
    
    # Find the mapping
    mapping = db.query(models.GitHubMapping).filter(
        models.GitHubMapping.id == mapping_id,
        models.GitHubMapping.user_id == current_user.id
    ).first()
    
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GitHub mapping not found")
    
    # If subdomain is changing, validate it
    if mapping.subdomain != mapping_update.subdomain:
        is_valid_subdomain, subdomain_error = validators.validate_subdomain(mapping_update.subdomain)
        if not is_valid_subdomain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=subdomain_error
            )
        
        # Check if the new subdomain is already in use
        existing = db.query(models.GitHubMapping).filter(models.GitHubMapping.subdomain == mapping_update.subdomain).first()
        if existing and existing.id != mapping_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This subdomain is already in use"
            )
    
    # Validate GitHub username
    is_valid_username, username_error = validators.validate_github_username(mapping_update.github_username)
    if not is_valid_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=username_error
        )
    
    # Validate repository name
    is_valid_repo, repo_error = validators.validate_repository_name(mapping_update.repository_name)
    if not is_valid_repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=repo_error
        )
    
    # Update DNS if subdomain or GitHub username changed
    if mapping.subdomain != mapping_update.subdomain or mapping.github_username != mapping_update.github_username:
        # Delete old DNS record
        cloudflare.delete_subdomain(mapping.subdomain)
        
        # Create new DNS record
        cf_result = cloudflare.create_github_pages_mapping(mapping_update.subdomain, mapping_update.github_username)
        
        if not cf_result["success"]:
            # If new DNS setup fails, try to restore the old one
            cloudflare.create_github_pages_mapping(mapping.subdomain, mapping.github_username)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update DNS: {cf_result['error']}"
            )
    
    # Update database record
    mapping.subdomain = mapping_update.subdomain
    mapping.github_username = mapping_update.github_username
    mapping.repository_name = mapping_update.repository_name
    
    db.commit()
    db.refresh(mapping)
    
    domain_name = os.getenv("DOMAIN_NAME", "sriox.com")
    
    return {
        "id": mapping.id,
        "subdomain": mapping.subdomain,
        "github_username": mapping.github_username,
        "repository_name": mapping.repository_name,
        "updated_at": mapping.updated_at,
        "url": f"https://{mapping.subdomain}.{domain_name}"
    }

@router.delete("/map-github/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_github_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a GitHub Pages mapping"""
    
    mapping = db.query(models.GitHubMapping).filter(
        models.GitHubMapping.id == mapping_id,
        models.GitHubMapping.user_id == current_user.id
    ).first()
    
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GitHub mapping not found")
    
    # Delete the DNS record
    cloudflare.delete_subdomain(mapping.subdomain)
    
    # Delete from database
    db.delete(mapping)
    db.commit()
    
    return None