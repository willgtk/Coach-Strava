FROM python:3.10-slim

WORKDIR /app

# Instala gcc e ferramentas de compilação dentro do container
RUN apt-get update && apt-get install -y gcc python3-dev tzdata && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Criar diretório de dados e usuário não-root para segurança
RUN mkdir -p /app/data \
    && useradd --create-home --no-log-init appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python", "src/bot_coach.py"]