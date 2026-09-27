# ---------- Stage 1: build ----------
FROM node:20-alpine AS build
WORKDIR /app

# Vite читает VITE_* переменные во время сборки.
# Пустой VITE_API_URL = same-origin: фронтенд обращается к /api на своём
# origin, а проксирует его nginx. Абсолютный адрес здесь привёл бы к
# обращению в обход прокси и CORS-отказу в браузере.
ARG VITE_API_URL=
ARG VITE_AUTH_MODE=jwt
ARG VITE_KEYCLOAK_URL=http://localhost:8080
ARG VITE_KEYCLOAK_REALM=rtk-crm
ARG VITE_KEYCLOAK_CLIENT_ID=rtk-crm-frontend
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_AUTH_MODE=$VITE_AUTH_MODE
ENV VITE_KEYCLOAK_URL=$VITE_KEYCLOAK_URL
ENV VITE_KEYCLOAK_REALM=$VITE_KEYCLOAK_REALM
ENV VITE_KEYCLOAK_CLIENT_ID=$VITE_KEYCLOAK_CLIENT_ID

ENV NODE_OPTIONS=--max-old-space-size=4096

RUN npm config set registry https://npm-mirror.gitverse.ru \
 && npm config set fetch-retries 5 \
 && npm config set fetch-retry-mintimeout 20000 \
 && npm config set fetch-retry-maxtimeout 120000

COPY package*.json ./
RUN npm install --no-audit --no-fund

COPY . .
RUN npm run build

# ---------- Stage 2: serve ----------
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]