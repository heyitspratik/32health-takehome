FROM python:3.8-slim

WORKDIR /app

COPY ../../requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pytest httpx pytest-asyncio

COPY . /app

ENV PYTHONPATH=/app

CMD ["pytest", "tests/test_app.py"] 
