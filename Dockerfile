# syntax=docker/dockerfile:1.7

# ---------- Stage 1: build the iframe app (Vite) ----------
FROM node:20-alpine AS app-builder
WORKDIR /src/app
COPY app/package.json app/package-lock.json ./
RUN npm ci
COPY app/ ./
RUN npm run build

# ---------- Stage 2: install the Python server and run ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /src

COPY server/pyproject.toml /src/server/
COPY server/customer_context_mcp /src/server/customer_context_mcp
RUN pip install /src/server

COPY --from=app-builder /src/app/dist /app/dist

EXPOSE 8787
CMD ["customer-context-mcp", "http", "--host", "0.0.0.0", "--port", "8787"]
