import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from .. import models
from ..db import get_db
from ..auth import get_current_active_user
from ..utils import validators

router = APIRouter(tags=["redirects"])

class RedirectCreate(BaseModel):
    name: str
    target_url: str

class RedirectUpdate(BaseModel):
    name: str
    target_url: str

@router.get("/redirects", response_model=List)
async def get_user_redirects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all redirects created by the current user"""
    redirects = db.query(models.Redirect).filter(models.Redirect.user_id == current_user.id).all()
    return redirects

@router.get("/redirect/count")
async def get_redirect_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get the count of redirects created by the current user"""
    count = db.query(func.count(models.Redirect.id)).filter(
        models.Redirect.user_id == current_user.id
    ).scalar()
    
    return {"count": count}

@router.post("/redirect", status_code=status.HTTP_201_CREATED)
async def create_redirect(
    redirect: RedirectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new redirect"""
    
    # Check if user has reached their limit of 2 redirects
    redirect_count = db.query(func.count(models.Redirect.id)).filter(
        models.Redirect.user_id == current_user.id
    ).scalar()
    
    if redirect_count >= 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have reached the limit of 2 redirects. Contact admin to add more."
        )
    
    # Validate the name
    if not redirect.name or len(redirect.name) < 1 or len(redirect.name) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect name must be between 1 and 50 characters"
        )
    
    # Alphanumeric and hyphens only for the name
    if not redirect.name.isalnum() and not all(c.isalnum() or c == '-' for c in redirect.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name can only contain letters, numbers, and hyphens"
        )
    
    # Validate the URL
    is_valid_url, error_msg = validators.validate_url(redirect.target_url)
    if not is_valid_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Check if name already exists
    existing = db.query(models.Redirect).filter(models.Redirect.name == redirect.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This redirect name is already in use"
        )
    
    # Create HTML file for the redirect
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        redirect_template_path = os.path.join(base_dir, "templates", "redirects", f"{redirect.name}.html")
        
        os.makedirs(os.path.dirname(redirect_template_path), exist_ok=True)
        
        with open(redirect_template_path, "w") as f:
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url={redirect.target_url}">
    <title>Redirecting to {redirect.target_url}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
        h1 {{ color: #333; }}
        p {{ color: #666; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Redirecting...</h1>
        <p>You are being redirected to: <br><a href="{redirect.target_url}">{redirect.target_url}</a></p>
        <p>If you are not redirected automatically, please click the link above.</p>
        <p><small>Powered by <a href="https://{os.getenv('DOMAIN_NAME', 'sriox.com')}">Sriox</a></small></p>
    </div>
</body>
</html>"""
            f.write(html_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create redirect file: {str(e)}"
        )
    
    # Save to database
    new_redirect = models.Redirect(
        name=redirect.name,
        target_url=redirect.target_url,
        user_id=current_user.id
    )
    
    db.add(new_redirect)
    db.commit()
    db.refresh(new_redirect)
    
    domain_name = os.getenv("DOMAIN_NAME", "sriox.com")
    
    return {
        "id": new_redirect.id,
        "name": new_redirect.name,
        "target_url": new_redirect.target_url,
        "created_at": new_redirect.created_at,
        "redirect_url": f"https://{domain_name}/{redirect.name}"
    }

@router.put("/redirect/{redirect_id}")
async def update_redirect(
    redirect_id: int,
    redirect_update: RedirectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update a redirect"""
    
    # Find the redirect
    redirect = db.query(models.Redirect).filter(
        models.Redirect.id == redirect_id,
        models.Redirect.user_id == current_user.id
    ).first()
    
    if not redirect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redirect not found")
    
    # If name is changing, validate it
    if redirect.name != redirect_update.name:
        if not redirect_update.name or len(redirect_update.name) < 1 or len(redirect_update.name) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redirect name must be between 1 and 50 characters"
            )
        
        if not redirect_update.name.isalnum() and not all(c.isalnum() or c == '-' for c in redirect_update.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name can only contain letters, numbers, and hyphens"
            )
        
        # Check if name already exists
        existing = db.query(models.Redirect).filter(models.Redirect.name == redirect_update.name).first()
        if existing and existing.id != redirect_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This redirect name is already in use"
            )
    
    # Validate the URL
    is_valid_url, error_msg = validators.validate_url(redirect_update.target_url)
    if not is_valid_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # If name or URL changed, update the HTML file
    if redirect.name != redirect_update.name or redirect.target_url != redirect_update.target_url:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            old_path = os.path.join(base_dir, "templates", "redirects", f"{redirect.name}.html")
            new_path = os.path.join(base_dir, "templates", "redirects", f"{redirect_update.name}.html")
            
            # Create new HTML file
            with open(new_path, "w") as f:
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url={redirect_update.target_url}">
    <title>Redirecting to {redirect_update.target_url}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
        h1 {{ color: #333; }}
        p {{ color: #666; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Redirecting...</h1>
        <p>You are being redirected to: <br><a href="{redirect_update.target_url}">{redirect_update.target_url}</a></p>
        <p>If you are not redirected automatically, please click the link above.</p>
        <p><small>Powered by <a href="https://{os.getenv('DOMAIN_NAME', 'sriox.com')}">Sriox</a></small></p>
    </div>
</body>
</html>"""
                f.write(html_content)
            
            # Delete old file if the name changed
            if redirect.name != redirect_update.name and os.path.exists(old_path):
                os.remove(old_path)
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update redirect file: {str(e)}"
            )
    
    # Update database record
    redirect.name = redirect_update.name
    redirect.target_url = redirect_update.target_url
    
    db.commit()
    db.refresh(redirect)
    
    domain_name = os.getenv("DOMAIN_NAME", "sriox.com")
    
    return {
        "id": redirect.id,
        "name": redirect.name,
        "target_url": redirect.target_url,
        "updated_at": redirect.updated_at,
        "redirect_url": f"https://{domain_name}/{redirect.name}"
    }

@router.delete("/redirect/{redirect_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_redirect(
    redirect_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a redirect"""
    
    redirect = db.query(models.Redirect).filter(
        models.Redirect.id == redirect_id,
        models.Redirect.user_id == current_user.id
    ).first()
    
    if not redirect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redirect not found")
    
    # Delete the HTML file
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "templates", "redirects", f"{redirect.name}.html")
        
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        # Continue with deletion even if file removal fails
        pass
    
    # Delete from database
    db.delete(redirect)
    db.commit()
    
    return None