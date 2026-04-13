FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"

ARG AWS_S3_ENDPOINT
ARG BASE_URL
ARG MODEL_NAME
ARG S3_PATH

ENV AWS_S3_ENDPOINT=$AWS_S3_ENDPOINT
ENV BASE_URL=$BASE_URL
ENV MODEL_NAME=$MODEL_NAME
ENV S3_PATH=$S3_PATH

# Installation
COPY pyproject.toml .
RUN uv sync 

# Copie de l'app
COPY app ./app
COPY src ./src

# Lancement
CMD ["bash", "-c", "./app/run.sh"]