FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install -e .

COPY . .

RUN useradd -m -u 1000 quantsage && chown -R quantsage:quantsage /app
USER quantsage

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "quantsage.main:app", "--host", "0.0.0.0", "--port", "8000"]
