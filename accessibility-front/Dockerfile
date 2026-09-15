# syntax=docker/dockerfile:1
FROM node:22-alpine

WORKDIR /app

# NEXT_PUBLIC_* values are inlined into the client bundle, so they are needed at build
# time. Everything else (API_URL, NEXT_CAS_CLIENT_SECRET, INTERNAL_AUTH_SECRET) is read
# at runtime from the container environment and must never be baked into the image.
ARG NEXT_PUBLIC_BASE_URL
ARG NEXT_PUBLIC_CAS_URL
ENV NEXT_PUBLIC_BASE_URL=${NEXT_PUBLIC_BASE_URL} \
    NEXT_PUBLIC_CAS_URL=${NEXT_PUBLIC_CAS_URL} \
    NEXT_TELEMETRY_DISABLED=1

# Dependencies first so this layer is cached across source changes. next-cas-client is
# installed from the vendored tarball referenced by package.json.
COPY package.json package-lock.json next-cas-client-1.3.6.tgz ./
RUN npm ci

COPY . .
RUN npm run build && chown -R node:node /app/.next

ENV NODE_ENV=production
USER node
EXPOSE 3000
CMD ["npm", "start"]
