import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from .api.routers import openneuro

app = FastAPI(default_response_class=ORJSONResponse)

app.include_router(openneuro.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", port=8000, reload=True)
