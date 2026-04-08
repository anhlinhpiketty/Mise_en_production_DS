FROM ubuntu:22.04

# Install Python et curl
RUN apt-get -y update && \
    apt-get install -y python3-pip curl

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
CMD ["uv", "run", "uvicorn", "app.api:app", "--host='0.0.0.0'"]