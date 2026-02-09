from backend.database import engine, Base
from backend import models
from backend.scheduler import start_scheduler
from backend.routers import assets, portfolio
from backend.i18n_utils import current_language
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastadmin import fastapi_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start scheduler on startup
    start_scheduler()
    yield
    # Actions on shutdown (e.g. scheduler.shutdown if needed)

app = FastAPI(title="Borsa Takip API", version="1.0.0", lifespan=lifespan)

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

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Setup admin panel
app.mount("/admin", fastapi_app)

@app.get("/")
async def read_root():
    return FileResponse('frontend/index.html')
