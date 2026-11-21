FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN useradd --create-home appuser \
    && mkdir -p /app/instance \
    && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "flask --app run setup-db && gunicorn --bind 0.0.0.0:8000 --workers 2 run:app"]