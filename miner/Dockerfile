FROM python:3.11-slim

WORKDIR /app

COPY main.py /app/main.py
RUN pip install --no-cache-dir requests

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]