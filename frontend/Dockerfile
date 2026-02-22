# ─── Frontend Dockerfile ───
# Multi-stage build: Node for build, Nginx for serve
# F-19: Production-grade containerization

FROM node:20-alpine AS builder
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY frontend/ .
RUN npm run build

# ─── Production Stage ───
FROM nginx:alpine AS production

# Security: Run as non-root
RUN addgroup -S dss && adduser -S dss -G dss

# Copy build artifacts
COPY --from=builder /app/build /usr/share/nginx/html

# Nginx config for SPA routing
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { try_files $uri $uri/ /index.html; } \
    location /api/ { proxy_pass http://backend:8000/; } \
}' > /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
