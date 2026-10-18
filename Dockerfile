FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml ./
COPY backend/ ./backend/
RUN pip install --no-deps . && useradd --create-home spark && mkdir -p /app/data && chown spark /app/data
COPY --from=web /web/dist ./frontend/dist/
USER spark
EXPOSE 8000
CMD ["uvicorn", "spark.main:app", "--host", "0.0.0.0", "--port", "8000"]
