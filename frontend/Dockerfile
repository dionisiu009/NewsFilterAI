# ==============================================================================
# NEWSFILTERAI - FRONTEND DOCKERFILE (React + Vite)
# ==============================================================================

# ЭТАП 1: Базовий
FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# ЭТАП 2: Локальна розробка (Vite)
FROM base AS development
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ЭТАП 3: Збірка статики
FROM base AS builder
RUN npm run build

# ЭТАП 4: Продакшен (Nginx)
FROM nginx:alpine AS production
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
