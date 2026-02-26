FROM python:3.10-slim

WORKDIR /app

# Instala gcc e ferramentas de compilação dentro do container
RUN apt-get update && apt-get install -y gcc python3-dev tzdata && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python", "src/bot_coach.py"]