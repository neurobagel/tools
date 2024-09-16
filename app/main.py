from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.utility import set_gh_credentials

from .api.routers import openneuro


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure info needed for GitHub authentication is read in before the FastAPI app starts up."""
    set_gh_credentials()
    yield


app = FastAPI(default_response_class=ORJSONResponse, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(openneuro.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", port=8000, reload=True)
