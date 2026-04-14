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
COPY frontend/app.py .

# Port Streamlit
EXPOSE 8501

# Lancement
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]