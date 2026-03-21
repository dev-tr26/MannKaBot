import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from pathlib import Path
from contextlib import asynccontextmanager

load_dotenv()

from routes.auth import router as auth_router
from routes.journal import router as journal_router
from routes.sarvam import router as sarvam_router
from database import connect_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db() 
    yield
    await close_db()    


app = FastAPI(
    title="MannKaBot - Voice AI Journal",
    description="A voice-powered AI journal that understands your mood",
    version="1.0.0",
    lifespan=lifespan   
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent / "frontend"
# app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(journal_router, prefix="/api/journal", tags=["Journal"])
app.include_router(sarvam_router, prefix="/api/sarvam", tags=["Sarvam AI"])


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/journal", response_class=HTMLResponse)
async def journal_page(request: Request):
    return templates.TemplateResponse("journal.html", {"request": request})

@app.get("/insights", response_class=HTMLResponse)
async def insights_page(request: Request):
    return templates.TemplateResponse("insights.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )