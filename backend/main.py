from backend.database import engine
from backend import models
from backend.scheduler import start_scheduler
from backend.routers import assets, portfolio, auth
from backend.i18n_utils import current_language
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import backend.admin
import os

# Load environment variables
load_dotenv()

from fastadmin import fastapi_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
        
    # Start scheduler on startup
    start_scheduler()
    yield
    # Actions on shutdown (e.g. scheduler.shutdown if needed)

app = FastAPI(title="Portfolio Tracker API", version="1.0.0", lifespan=lifespan)

# CORS Configuration
# In production, specify exact origins instead of ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for language handling
@app.middleware("http")
async def language_middleware(request: Request, call_next):
    lang = request.query_params.get("lang")
    if not lang:
        lang = request.cookies.get("admin_lang", "en")
    
    # Set context variable
    if lang in ["en", "tr"]:
        token = current_language.set(lang)
    else:
        token = current_language.set("en")
        
    response = await call_next(request)
    
    # If lang was in query params, set cookie
    if request.query_params.get("lang") and lang in ["en", "tr"]:
        response.set_cookie(key="admin_lang", value=lang)
        
    current_language.reset(token)
    return response

# Mount static files (JS, CSS)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Include routers
app.include_router(assets.router)
app.include_router(portfolio.router)
app.include_router(auth.router)

# Setup admin panel
app.mount("/admin", fastapi_app)

@app.get("/")
async def read_root():
    return FileResponse('frontend/index.html')

@app.get("/profile.html")
async def read_profile():
    return FileResponse('frontend/profile.html')

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    file_path = "frontend/static/favicon.ico"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return Response(status_code=404)
