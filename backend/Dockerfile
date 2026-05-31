FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements-render.txt .

RUN pip install --no-cache-dir --prefer-binary --default-timeout=300 \
    numpy==1.26.4 pandas==2.2.2

RUN pip install --no-cache-dir --prefer-binary --default-timeout=300 -r requirements-render.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
