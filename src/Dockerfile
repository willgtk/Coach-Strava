FROM python:3.10-slim

WORKDIR /app

# O pulo do gato: instalamos o gcc e ferramentas de compilação dentro do container
RUN apt-get update && apt-get install -y gcc python3-dev tzdata && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot_coach.py"]