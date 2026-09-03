# ── Frontend Dockerfile (multi-stage) ──────────────────────────────
# Stage 1: build the React SPA with Vite
# Stage 2: serve with nginx
# ───────────────────────────────────────────────────────────────────

FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Runtime stage ──────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
