import os
import tempfile
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models
from ..db import get_db
from ..auth import get_current_active_user
from ..utils import cloudflare, unzip, validators

router = APIRouter(tags=["website-uploads"])

MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 35000000))  # 35MB in bytes

@router.get("/uploads", response_model=List)
async def get_user_websites(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all websites uploaded by the current user"""
    websites = db.query(models.Website).filter(models.Website.user_id == current_user.id).all()
    return websites

@router.get("/upload/count")
async def get_website_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get the count of websites uploaded by the current user"""
    count = db.query(func.count(models.Website.id)).filter(
        models.Website.user_id == current_user.id
    ).scalar()
    
    return {"count": count}

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_website(
    subdomain: str = Form(...),
    zip_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Upload a new website as a zip file"""
    
    # Check if user has reached their limit of 2 websites
    website_count = db.query(func.count(models.Website.id)).filter(
        models.Website.user_id == current_user.id
    ).scalar()
    
    if website_count >= 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have reached the limit of 2 website uploads. Contact admin to add more."
        )
    
    # Validate subdomain
    is_valid, error_msg = validators.validate_subdomain(subdomain)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    
    # Check if subdomain already exists
    existing = db.query(models.Website).filter(models.Website.subdomain == subdomain).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This subdomain is already in use"
        )
    
    # Check file size
    if zip_file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the limit of {MAX_UPLOAD_SIZE // 1000000} MB"
        )
    
    # Save uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        shutil.copyfileobj(zip_file.file, temp_file)
    
    # Extract the website
    extract_result = unzip.extract_website(temp_file.name, subdomain)
    
    if not extract_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=extract_result["error"]
        )
    
    # Create a DNS record in Cloudflare
    server_ip = os.getenv("SERVER_IP", "127.0.0.1")  # Should be the VPS IP
    cf_result = cloudflare.create_subdomain(subdomain, "A", server_ip)
    
    if not cf_result["success"]:
        # Cleanup the extracted folder if DNS setup fails
        unzip.delete_website_folder(subdomain)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set up DNS: {cf_result['error']}"
        )
    
    # Save to database
    new_website = models.Website(
        subdomain=subdomain,
        folder_path=extract_result["relative_path"],
        user_id=current_user.id
    )
    
    db.add(new_website)
    db.commit()
    db.refresh(new_website)
    
    return {
        "id": new_website.id,
        "subdomain": new_website.subdomain,
        "created_at": new_website.created_at,
        "url": f"https://{subdomain}.{os.getenv('DOMAIN_NAME', 'sriox.com')}"
    }

@router.put("/upload/{website_id}")
async def update_website(
    website_id: int,
    subdomain: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update a website's subdomain"""
    
    # Find the website
    website = db.query(models.Website).filter(
        models.Website.id == website_id,
        models.Website.user_id == current_user.id
    ).first()
    
    if not website:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")
    
    # If subdomain is not changing, return early
    if website.subdomain == subdomain:
        return website
    
    # Validate the new subdomain
    is_valid, error_msg = validators.validate_subdomain(subdomain)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    
    # Check if the new subdomain is already in use
    existing = db.query(models.Website).filter(models.Website.subdomain == subdomain).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This subdomain is already in use"
        )
    
    # Delete old DNS record
    cloudflare.delete_subdomain(website.subdomain)
    
    # Create new DNS record
    server_ip = os.getenv("SERVER_IP", "127.0.0.1")
    cf_result = cloudflare.create_subdomain(subdomain, "A", server_ip)
    
    if not cf_result["success"]:
        # If new DNS setup fails, try to restore the old one
        cloudflare.create_subdomain(website.subdomain, "A", server_ip)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update DNS: {cf_result['error']}"
        )
    
    # Rename the folder
    old_path = os.path.join("static_sites", website.subdomain)
    new_path = os.path.join("static_sites", subdomain)
    
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        old_full_path = os.path.join(base_dir, old_path)
        new_full_path = os.path.join(base_dir, new_path)
        
        # Move the folder
        if os.path.exists(old_full_path):
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
            shutil.move(old_full_path, new_full_path)
    except Exception as e:
        # If folder rename fails, attempt to revert DNS changes
        cloudflare.delete_subdomain(subdomain)
        cloudflare.create_subdomain(website.subdomain, "A", server_ip)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update website folder: {str(e)}"
        )
    
    # Update database record
    website.subdomain = subdomain
    website.folder_path = new_path
    
    db.commit()
    db.refresh(website)
    
    return website

@router.delete("/upload/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_website(
    website_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a website"""
    
    website = db.query(models.Website).filter(
        models.Website.id == website_id,
        models.Website.user_id == current_user.id
    ).first()
    
    if not website:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")
    
    # Delete the DNS record
    cloudflare.delete_subdomain(website.subdomain)
    
    # Delete the website folder
    unzip.delete_website_folder(website.subdomain)
    
    # Delete from database
    db.delete(website)
    db.commit()
    
    return None