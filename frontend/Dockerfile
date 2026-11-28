# syntax=docker/dockerfile:1
# Builds one of the two apps: docker build --build-arg APP=buyer|admin -f frontend/Dockerfile frontend
FROM node:26-alpine AS build
ARG APP=buyer
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npx ng build ${APP} --configuration production

FROM nginx:1.31-alpine AS runtime
ARG APP=buyer
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /src/dist/${APP}/browser /usr/share/nginx/html
ENV API_UPSTREAM=http://api:8000 \
    MEDIA_ORIGIN=http://localhost:8333
EXPOSE 80
