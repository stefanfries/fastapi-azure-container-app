from fastapi import FastAPI

from app.routers import users, welcome

app = FastAPI()
app.include_router(welcome.router)
app.include_router(users.router)


def main() -> None:
    """Main entry point of the app"""
    pass


if __name__ == "__main__":
    main()

"""
To run the app, use the command below, and then go to http://localhost:8000/docs in your browser.
uvicorn --host 127.0.0.1 --port 8080 --reload app.main:app
"""
#    import uvicorn
#    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
# The main function is empty, but it is a placeholder for future code.
