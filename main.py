"""

MindBridge - Real-time Mind-Link Collaboration System
Inspired by Ino Yamanaka's telepathic coordination

"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import close_db, init_db
from routers import Sessions, Signals, Users, Ws
from services.Background import BackgroundTaskManager
from services.Nlp import get_classifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

task_manager = BackgroundTaskManager()



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MindBridge initializing neural pathways...")
    await init_db()
    await task_manager.start()
    # Warm up NLP model before first request hits
    logger.info("Warming up NLP classifier...")
    get_classifier()
    logger.info("NLP classifier ready")
    yield
    logger.info("MindBridge shutting down neural pathways...")
    await task_manager.stop()
    await close_db()

app = FastAPI(
    title="MindBridge API",
    description="A real time mindlink collaboration system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware, # type: ignore[arg-type]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(Users.router, prefix="/api/users", tags=["users"])
app.include_router(Sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(Signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(Ws.router, prefix="/api/ws", tags=["ws"])

@app.get("/api/health")
async def health_check():
    return {"status": "neural_link_active", "version": "1.0.0"}
