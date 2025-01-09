"""
Main Module for the FastAPI Application

To run the app, use the command below, and then go to http://localhost:8000/docs in your browser.
uvicorn --host 127.0.0.1 --port 8080 --reload app.main:app

The main function is empty, but it is a placeholder for future code.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.middleware import log_client_ip_middleware
from app.routers import basedata, depots, users, welcome

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.middleware("http")(log_client_ip_middleware)

app.include_router(welcome.router)
app.include_router(users.router)
app.include_router(basedata.router)
app.include_router(depots.router)


def main() -> None:
    """
    Entry point for running the FastAPI application using Uvicorn.
    This function starts the Uvicorn server with the specified application instance,
    host, port, and reload settings.
    Parameters:
    None
    Returns:
    None
    """

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
    return None


if __name__ == "__main__":
    main()
