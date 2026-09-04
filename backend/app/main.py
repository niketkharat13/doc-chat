from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import logging

from app.llm.gemini import llm
from app.database.db import init_db
from app.routers.chat import chat

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="RAG Application", version="1.0.0", lifespan=lifespan)

# Configure basic logging
logging.basicConfig(level=logging.INFO)

app.include_router(chat.router, prefix="/api", tags=["Chat"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    return {"status": "ok"}