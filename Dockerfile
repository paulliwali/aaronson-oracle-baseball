# Use python 3.11
FROM python:3.11-slim

# Install Node.js for building frontend
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory in the container
WORKDIR /app

# Copy frontend package files and install dependencies
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm ci

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Go back to app root
WORKDIR /app

# Copy pyproject.toml and install Python dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy the rest of the application code
COPY . .

# Expose port 8000 for FastAPI
EXPOSE 8000

# Command to run the FastAPI app
CMD ["python", "backend/run.py"]
