FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=5000 DATABASE_PATH=/app/data/queueless.db COOKIE_SECURE=false
RUN mkdir -p /app/data
EXPOSE 5000
CMD ["sh","-c","gunicorn --workers 1 --threads 4 --bind 0.0.0.0:${PORT} app:app"]
