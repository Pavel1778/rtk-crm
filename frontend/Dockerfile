# ---------- Stage 1: build ----------
FROM node:20-alpine AS build
WORKDIR /app

# Vite читает VITE_* переменные во время сборки.
# Пустой VITE_API_URL = same-origin: фронтенд обращается к /api на своём
# origin, а проксирует его nginx. Абсолютный адрес здесь привёл бы к
# обращению в обход прокси и CORS-отказу в браузере.
ARG VITE_API_URL=
ARG VITE_KEYCLOAK_URL=http://localhost:8080
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_KEYCLOAK_URL=$VITE_KEYCLOAK_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---------- Stage 2: serve ----------
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]