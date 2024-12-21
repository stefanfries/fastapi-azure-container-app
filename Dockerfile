FROM python:3.12.8-slim

RUN mkdir -p /app

# Set the working directory
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt /app/

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the application source code
COPY ./app /app/

EXPOSE 8080

# As main module is located in /app, set the PYTHONPATH environment variable to include /app
# so Python can find it
# ENV PYTHONPATH=/

# Command to run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8080"]
