"""

MindBridge A real time mindlink collaboration system
Inspired by Ino Yamanaka's Telepathic Coordination

"""

import asyncio # allows use in await/async syntax
import logging # log for better debugging errors
from contextlib import asynccontextmanager # make asynchronous context managers

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

#from .database import init_db, close_db

logging.basicConfig(level=logging.INFO) # do basic config for logging system
logger = logging.getLogger(__name__) # return logger with specified name

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MindBridge initializing neural pathways...")
    yield
    logger.info("MindBridge shutting down neural pathways...")

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

@app.get("/api/health")
async def health_check():
    return {"status": "neural_link_active", "version": "1.0.0"}
