FROM node:20-bookworm-slim AS build
WORKDIR /src
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 600000
COPY frontend/ ./
RUN rm -f .env
ENV REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false NODE_OPTIONS=--max-old-space-size=2048
RUN yarn build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/build /srv
