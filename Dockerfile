FROM python:3.11-slim

WORKDIR /app

# System deps for some packages (may be expanded if build errors occur)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc git wget curl ca-certificates pkg-config libglib2.0-0 libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Vercel sets $PORT. Default to 8000 for local runs.
ENV PORT=${PORT:-8000}
EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.server:app --host 0.0.0.0 --port ${PORT}"]
