"""
Main Module for the FastAPI Application

To run the app, use the command below, and then go to http://localhost:8000/docs in your browser.
uvicorn --host 127.0.0.1 --port 8080 --reload app.main:app

The main function is empty, but it is a placeholder for future code.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.middleware import log_client_ip_middleware
from app.routers import basedata, depots, history, pricedata, users, welcome


class CustomJSONResponse(JSONResponse):
    """
    Custom JSON response class that sets the media type to "application/json; charset=utf-8".
    This is necessary to ensure that the JSON response (containing German Umlauts) is correctly formatted, especially for Apple devices.
    Attributes:
        media_type (str): The media type for the response, set to "application/json; charset=utf-8".
    """

    media_type = "application/json; charset=utf-8"


app = FastAPI(default_response_class=CustomJSONResponse)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.middleware("http")(log_client_ip_middleware)

app.include_router(welcome.router)
app.include_router(users.router)
app.include_router(basedata.router)
app.include_router(depots.router)
app.include_router(pricedata.router)
app.include_router(history.router)


def main() -> None:
    """
    Entry point for running the FastAPI application using Uvicorn.
    This function starts the Uvicorn server with the specified application instance,
    host, port, and reload settings.
    Parameters:
        None
        None
        None
    """

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=False)
    return None


if __name__ == "__main__":
    main()
