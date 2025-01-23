from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, ORJSONResponse, RedirectResponse

from app.api.utility import ROOT_PATH, set_gh_credentials

from .api.routers import openneuro

FAVICON_URL = "https://raw.githubusercontent.com/neurobagel/documentation/main/docs/imgs/logo/neurobagel_favicon.png"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure info needed for GitHub authentication is read in before the FastAPI app starts up."""
    set_gh_credentials()
    yield


app = FastAPI(
    root_path=ROOT_PATH,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    # We will override the default docs with our own endpoints with a custom favicon
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# TODO: Should we exclude the root endpoint from the schema for a cleaner docs?
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    """
    Display a welcome message and a link to the API documentation.
    """
    return f"""
    <html>
        <body>
            <h1>Welcome to the API for <a href="https://github.com/OpenNeuroDatasets-JSONLD" target="_blank">Neurobagel-annotated OpenNeuro Datasets!</a></h1>
            <p>Please visit the <a href="{request.scope.get("root_path", "")}/docs">API documentation</a> to view available API endpoints.</p>
        </body>
    </html>
    """


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Overrides the default favicon with a custom one.
    """
    return RedirectResponse(url=FAVICON_URL)


@app.get("/docs", include_in_schema=False)
def overridden_swagger(request: Request):
    """
    Overrides the Swagger UI HTML for the "/docs" endpoint.
    """
    return get_swagger_ui_html(
        openapi_url=f"{request.scope.get('root_path', '')}/openapi.json",
        title="Neurobagel OpenNeuro Datasets API",
        swagger_favicon_url=FAVICON_URL,
    )


@app.get("/redoc", include_in_schema=False)
def overridden_redoc(request: Request):
    """
    Overrides the Redoc HTML for the "/redoc" endpoint.
    """
    return get_redoc_html(
        openapi_url=f"{request.scope.get('root_path', '')}/openapi.json",
        title="Neurobagel OpenNeuro Datasets API",
        redoc_favicon_url=FAVICON_URL,
    )


app.include_router(openneuro.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", port=8000, reload=True)
