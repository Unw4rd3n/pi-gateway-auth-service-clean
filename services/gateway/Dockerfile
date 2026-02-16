FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .

COPY services/gateway /app/services/gateway

EXPOSE 8001
CMD ["uvicorn", "services.gateway.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
