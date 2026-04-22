# Base Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Poetry globally
RUN pip install --no-cache-dir poetry

# Copy project files
COPY pyproject.toml poetry.lock* ./
COPY . .

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Expose port
EXPOSE 8000

# Run FastAPI with gunicorn (production — no --reload, multi-worker)
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "orchestrator.main:app", "--bind", "0.0.0.0:8000"]
