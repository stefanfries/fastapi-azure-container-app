FROM python:3.13-slim

RUN mkdir -p /code

# Set the working directory
WORKDIR /code

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt /code/

# Install dependencies and clean up pip cache
RUN pip install --upgrade pip && \
    pip install -r requirements.txt&& \
    rm -rf /root/.cache/pip

# Copy the application source code
COPY ./app /code/app/

EXPOSE 8080

# As main module is located in /app, set the PYTHONPATH environment variable to include /app
# so Python can find it
ENV PYTHONPATH=/code

# this seems to be the root course of the problem
# Set the working directory and alyze further
# WORKDIR /

# Command to run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
