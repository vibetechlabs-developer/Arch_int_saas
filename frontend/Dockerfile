# syntax=docker/dockerfile:1
#
# Multi-stage build for the INT Projects SaaS frontend.
# Stages: base -> dev (local development, hot-reload) / builder -> production
# (nginx serving the static Vite build, no Node runtime shipped).
#
# VITE_API_BASE_URL is baked into the JS bundle at build time (Vite's own
# convention -- there is no runtime env injection for a static SPA build),
# from frontend/.env.production. Edit that file to the real deployed API
# origin before building this image for a real deployment.

# --- base: shared Node install ----------------------------------------------
FROM node:20-slim AS base
WORKDIR /app

# --- dev: hot-reload target, matches `npm run dev` locally ------------------
FROM base AS dev
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "run", "dev", "--", "--host"]

# --- builder: production JS build only, isolated from the runtime image ----
FROM base AS builder
COPY package*.json ./
RUN npm ci
COPY . .
# --outDir overrides vite.config.ts's dev-convenience outDir (which points
# outside this directory, into ../backend/staticfiles/frontend -- not
# reachable from an isolated frontend-only Docker build context).
RUN npx tsc && npx vite build --outDir dist

# --- production: static files served via nginx, no Node in the final image -
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
