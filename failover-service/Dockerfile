FROM python:3.10-slim

WORKDIR /app

RUN pip install psycopg2-binary

COPY monitor.py .

CMD ["python", "-u", "monitor.py"]