# Tablero Next.js. Lee las versiones aprobadas montadas en pipeline/data/processed.
FROM node:22.21.1-slim

ENV HUSKY=0 \
    NEXT_TELEMETRY_DISABLED=1 \
    COREPACK_ENABLE_DOWNLOAD_PROMPT=0

WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build --webpack

EXPOSE 3000
CMD ["pnpm", "start", "-H", "0.0.0.0"]
