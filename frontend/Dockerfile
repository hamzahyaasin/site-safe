FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Vite bakes these into the bundle at build time.
ARG VITE_API_URL=http://localhost:8000/api/
ARG VITE_WS_URL=ws://localhost:8000/ws/dashboard/
ARG VITE_SITE_NAME=Site-Safe
ENV VITE_API_URL=$VITE_API_URL VITE_WS_URL=$VITE_WS_URL VITE_SITE_NAME=$VITE_SITE_NAME
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
