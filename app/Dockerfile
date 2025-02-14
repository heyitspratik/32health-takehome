FROM python:3.8-slim

WORKDIR /app

COPY ../../requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pytest httpx pytest-asyncio


COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
