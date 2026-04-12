from sys import prefix
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import uuid
import json
from typing import Dict
from middleware import RedisSessionMiddleware, LoadAwareMiddleware
from API_Layer.routes.design import router as design_router
from API_Layer.routes.user import router as user_router
from API_Layer.routes.chat import router as chat_router
import logging
import os
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from API_Layer.Redis.redis import RedisSessionStore

load_dotenv()


PROJECT_NAME = "server"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True,
)
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger(PROJECT_NAME).setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app):
    # Add any startup code here if needed
    redis_store = RedisSessionStore(redis_url="redis://localhost:6379")
    print(redis_store)
    app.state.redis_store = redis_store
    yield
    print("server shutting down.")
    # Add any shutdown/cleanup code here if needed


app = FastAPI(lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(RedisSessionMiddleware)
# app.add_middleware(LoadAwareMiddleware)


app.include_router(design_router, prefix="/design")
app.include_router(user_router, prefix="/auth")
app.include_router(chat_router, prefix="/chat")


# @app.get("/")
# async def root(request: Request):
#     return {
#         "message": "Server running",
#         "user_id": request.state.user_id,
#         "session": request.state.session,
#     }
