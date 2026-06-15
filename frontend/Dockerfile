FROM node:22-alpine AS builder 

RUN apk update && apk upgrade

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci 

COPY . .

# API_BASE defaults to /api so nginx can proxy it — override at build time if needed
ARG VITE_API_BASE=/api
ARG VITE_WS_BASE=/api/ws
ENV VITE_API_BASE=$VITE_API_BASE
ENV VITE_WS_BASE=$VITE_WS_BASE

RUN npm run build 

# ── Production stage ────────────────────────────────────────────────────────
FROM nginx:alpine
RUN apk update && apk upgrade


# Copy build assets 
COPY --from=builder /app/dist /usr/share/nginx/html 

# Nginx config: serve the SPA and proxy /api → backend
COPY nginx.conf /etc/nginx/conf.d/default.conf
 
EXPOSE 80