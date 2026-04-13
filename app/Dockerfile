FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"

# Installe d'abord PyTorch CPU AVANT uv sync
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu --no-cache-dir

COPY app ./app
COPY src ./src

COPY pyproject.toml .
RUN uv sync

ARG AWS_S3_ENDPOINT BASE_URL MODEL_NAME S3_PATH
ENV AWS_S3_ENDPOINT=$AWS_S3_ENDPOINT \
    BASE_URL=$BASE_URL \
    MODEL_NAME=$MODEL_NAME \
    S3_PATH=$S3_PATH

CMD ["bash", "-c", "./app/run.sh"]