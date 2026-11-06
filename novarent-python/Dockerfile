FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/
COPY tests/ ./tests/
COPY data/ ./data/
COPY run_tests.py ./
RUN pip install --no-cache-dir '.[dev]'
EXPOSE 8000
CMD ["sh", "-c", "uvicorn novarent.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
