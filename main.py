"""

MindBridge - Real-time Mind-Link Collaboration System
Inspired by Ino Yamanaka's telepathic coordination

"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, close_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from routers import Users, Sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MindBridge initializing neural pathways...")
    await init_db()
    yield
    logger.info("MindBridge shutting down neural pathways...")
    await close_db()

app = FastAPI(
    title="MindBridge API",
    description="A real time mindlink collaboration system",
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

app.include_router(Users.router, prefix="/api/users", tags=["users"])
app.include_router(Sessions.router, prefix="/api/sessions", tags=["sessions"])

@app.get("/api/health")
async def health_check():
    return {"status": "neural_link_active", "version": "1.0.0"}