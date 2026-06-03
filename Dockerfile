# G42 Agentathon - Use Case 24 - Personal Finance Agent
# Multi-stage clean Python 3.11 image. Builds in ~90s, runs on CPU.

FROM python:3.11-slim

LABEL org.opencontainers.image.title="g42-personal-finance-agent"
LABEL org.opencontainers.image.description="Use Case 24 - Multi-agent personal finance assistant for UAE"

WORKDIR /app

# Python tuning
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CREWAI_TELEMETRY_OPT_OUT=true

# System deps: curl for HEALTHCHECK, ca-certificates so pip can validate TLS
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Configure pip to trust PyPI hosts (works on both clean and corporate-SSL-inspected networks)
RUN pip config set global.trusted-host "pypi.org pypi.python.org files.pythonhosted.org"

# Install Python deps first (caching layer)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the application code
COPY . .

# Logs folder
RUN mkdir -p logs

# Hackathon mandates port 8000
EXPOSE 8000

# Healthcheck so judges' evaluator can verify readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Run.py binds to 0.0.0.0 (NOT localhost) per technical execution requirements
CMD ["python", "run.py"]
