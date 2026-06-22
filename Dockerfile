FROM python:3.12-slim

LABEL org.opencontainers.image.title="Mergewall"
LABEL org.opencontainers.image.description="AI Merge Governance Runtime — block high-risk AI-generated code from entering production"
LABEL org.opencontainers.image.licenses="MIT"

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir -e .

USER appuser

ENTRYPOINT ["mergewall"]
CMD ["--help"]
