FROM node:20-bookworm-slim AS build
WORKDIR /src
COPY frontend/package.json deploy/frontend.lockfil[e] ./
RUN if [ -f frontend.lockfile ]; then mv frontend.lockfile yarn.lock && yarn install --frozen-lockfile --network-timeout 600000; else yarn install --network-timeout 600000; fi
COPY frontend/ ./
RUN rm -f .env
RUN node -e "const f='public/index.html',fs=require('fs');let h=fs.readFileSync(f,'utf8');h=h.replace(/<script src=\"https:\/\/assets\.emergent\.sh[^>]*><\/script>/g,'').replace(/<script>\s*!\(function \(t, e\)[\s\S]*?<\/script>/g,'');fs.writeFileSync(f,h)"
ENV REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false NODE_OPTIONS=--max-old-space-size=2048
RUN yarn build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/build /srv
