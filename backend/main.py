import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import engine, get_db, Base
from .routes import upload, redirect, github, user
from . import models
from .auth import get_current_active_user

# Create tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sriox Platform",
    description="Self-hosted platform for website hosting, redirects, and GitHub Pages mappings",
    version="1.0.0"
)

# Get allowed origins from environment or use default for development
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

# CORS middleware with proper configuration for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# Mount static files
current_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))

# Include routers
app.include_router(user.router)
app.include_router(upload.router)
app.include_router(redirect.router)
app.include_router(github.router)

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Sriox Platform</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    line-height: 1.6;
                }
                header {
                    text-align: center;
                    margin: 2em 0;
                }
                h1 {
                    color: #333;
                }
                .cta {
                    display: flex;
                    justify-content: center;
                    gap: 20px;
                    margin: 2em 0;
                }
                .button {
                    display: inline-block;
                    background-color: #4F46E5;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                    text-decoration: none;
                    font-weight: 500;
                }
                .button:hover {
                    background-color: #4338CA;
                }
                footer {
                    margin-top: 3em;
                    text-align: center;
                    color: #6B7280;
                    font-size: 0.9em;
                }
            </style>
        </head>
        <body>
            <header>
                <h1>Welcome to Sriox Platform</h1>
                <p>Your self-hosted solution for website hosting, redirects, and GitHub Pages mappings</p>
            </header>
            
            <div class="cta">
                <a href="/dashboard" class="button">Dashboard</a>
                <a href="/login" class="button">Login</a>
                <a href="/signup" class="button">Sign Up</a>
            </div>
            
            <section>
                <h2>Features</h2>
                <ul>
                    <li>Host your websites under custom subdomains</li>
                    <li>Create short redirect links</li>
                    <li>Map GitHub Pages to custom subdomains</li>
                </ul>
            </section>
            
            <footer>
                <p>&copy; 2025 Sriox Platform. All rights reserved.</p>
            </footer>
        </body>
    </html>
    """

# Serve hosted websites at subdomains
@app.get("/subdomain/{subdomain}", include_in_schema=False)
async def get_subdomain_website(subdomain: str, path: str = "", db: Session = Depends(get_db)):
    # Find the website in the database
    website = db.query(models.Website).filter(models.Website.subdomain == subdomain).first()
    
    if not website:
        raise HTTPException(status_code=404, detail="Subdomain not found")
    
    # Build the path to the requested file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, website.folder_path)
    
    # If path is empty, try to serve index.html
    if not path:
        file_path = os.path.join(file_path, "index.html")
    else:
        file_path = os.path.join(file_path, path)
    
    # Check if the file exists
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Serve the file
    return FileResponse(file_path)

# Serve redirect pages
@app.get("/{redirect_name}", include_in_schema=False)
async def get_redirect(redirect_name: str, request: Request, db: Session = Depends(get_db)):
    # Check if this is a redirect
    redirect = db.query(models.Redirect).filter(models.Redirect.name == redirect_name).first()
    
    if not redirect:
        # Not a redirect, return 404
        raise HTTPException(status_code=404, detail="Redirect not found")
    
    # Serve the redirect template
    return templates.TemplateResponse(f"redirects/{redirect_name}.html", {"request": request})

# Dashboard page template
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, current_user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Login page template
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Signup page template
@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

# Health check endpoint for container orchestration
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sriox-platform"}