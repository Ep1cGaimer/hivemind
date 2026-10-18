# The default image is the dependency-light offline memory profile. Build with
# HIVEMIND_PROFILE=live to include the pinned FalkorDB Python client; the
# FalkorDB server remains a separately managed container.
FROM python:3.11.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt requirements.lock ./
RUN python -m pip install --no-cache-dir --requirement requirements.txt
ARG HIVEMIND_PROFILE=offline
RUN if [ "$HIVEMIND_PROFILE" = "live" ]; then \
      python -m pip install --no-cache-dir --requirement requirements.lock; \
    fi

COPY hivemind ./hivemind
COPY demo ./demo
COPY web ./web

EXPOSE 8000

CMD ["python", "-m", "hivemind", "--host", "0.0.0.0", "--port", "8000"]
