FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .

# Install smaller packages first, then large ones with longer timeouts
RUN pip install --no-cache-dir --prefer-binary --default-timeout=600 \
    fastapi==0.115.0 PyJWT==2.9.0 uvicorn==0.30.0 python-dotenv==1.0.1 \
    yfinance==0.2.44 joblib==1.4.2 scikit-learn==1.5.1 \
    pydantic==2.8.2 seaborn==0.13.2 matplotlib==3.9.2 \
    groq==0.37.1 anakin-sdk==0.1.0 psycopg2-binary==2.9.9 \
    sendgrid==6.11.0 sqlalchemy==2.0.35 \
    langgraph==0.2.67 langchain-core==0.3.33

# Install large ML packages with robust retry mechanism
RUN pip install --no-cache-dir --prefer-binary --default-timeout=900 --retries=5 \
    numpy==1.26.4 pandas==2.2.2 transformers==4.44.0 || \
    pip install --no-cache-dir --prefer-binary --default-timeout=900 --retries=5 \
    numpy==1.26.4 pandas==2.2.2 transformers==4.44.0

RUN pip install --no-cache-dir --prefer-binary --default-timeout=900 --retries=5 \
    tensorflow==2.17.0 tf-keras==2.17.0 || \
    pip install --no-cache-dir --prefer-binary --default-timeout=900 --retries=5 \
    tensorflow==2.17.0 tf-keras==2.17.0

RUN pip install --no-cache-dir --prefer-binary --default-timeout=900 --retries=5 \
    torch==2.3.1 || \
    pip install --no-cache-dir --prefer-binary --default-timeout=900 --retries=5 \
    torch==2.3.1

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
