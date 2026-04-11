FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"

# Installation
COPY pyproject.toml .
RUN uv sync 

# Copie de l'app
COPY app ./app
COPY src ./src

# Lancement
CMD ["bash", "-c", "./app/run.sh"]