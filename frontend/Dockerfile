# ── Build stage ──
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm config set registry https://registry.npmmirror.com && npm install -g pnpm && pnpm config set registry https://registry.npmmirror.com && pnpm install --frozen-lockfile

COPY . .
ARG VITE_API_BASE_URL=/api/v1
RUN VITE_API_BASE_URL=$VITE_API_BASE_URL pnpm run build

# ── Serve stage ──
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
