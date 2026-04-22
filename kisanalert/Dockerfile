FROM python:3.12-slim

# Prevent writing .pyc files and enable unbuffered stdout
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install system dependencies (helpful for XGBoost/Scipy if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set dynamic port for Google Cloud Run
ENV PORT 8080
EXPOSE $PORT

# Start the uvicorn server serving the FastAPI app
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:=8080}
