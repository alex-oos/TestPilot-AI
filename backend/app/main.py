import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.logger import setup_logger, logger
from app.core import database

# Initialize logger
setup_logger()
logger.info("Initializing FastAPI Application...")

app = FastAPI(
    title="AI Test Platform API",
    description="A centralized testing platform for AI generated content.",
    version="1.0.0"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    database.init_db()
    logger.info("Application started up successfully.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down.")
