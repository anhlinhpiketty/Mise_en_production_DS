FROM ubuntu:22.04

# Install Python et curl
RUN apt-get -y update && \
    apt-get install -y python3-pip curl

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"

# Dossier de travail
WORKDIR /app

# Installation
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copie de l'app
COPY app.py .

# Port Streamlit
EXPOSE 8501

# Lancement
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]