FROM node:22-slim AS frontend-builder

WORKDIR /app

COPY frontend/package.json frontend/pnpm-lock.yaml ./frontend/
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate

WORKDIR /app/frontend
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm build


FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY web/ ./web/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/
COPY scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh
RUN chmod +x ./scripts/docker-entrypoint.sh

ENV LETS_GIT_REPO=/data/lets-artifacts
ENV LETS_FRONTEND_DIST=/app/frontend/dist

EXPOSE 8000

CMD ["./scripts/docker-entrypoint.sh"]
