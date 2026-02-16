FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .

COPY services/auth_service /app/services/auth_service

EXPOSE 8000
CMD ["uvicorn", "services.auth_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
