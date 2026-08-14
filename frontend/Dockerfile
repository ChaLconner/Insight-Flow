# Base image
FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Next rewrites resolve during build; avoid frontend-container loopback.
ARG API_URL=http://backend:8000
ENV API_URL=${API_URL}

# Next.js collects completely anonymous telemetry data about general usage.
# Learn more here: https://nextjs.org/telemetry
# Uncomment the following line in case you want to disable telemetry during the build.
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build \
    && mkdir -p /app/runtime \
    && if [ -f /app/.next/standalone/server.js ]; then \
         cp -a /app/.next/standalone/. /app/runtime/; \
       elif [ -f /app/.next/standalone/frontend/server.js ]; then \
         cp -a /app/.next/standalone/frontend/. /app/runtime/; \
       elif [ -f /app/.next/standalone/app/server.js ]; then \
         cp -a /app/.next/standalone/app/. /app/runtime/; \
       else \
         echo "Next standalone server.js was not generated" >&2; \
         exit 1; \
       fi

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
# Uncomment the following line in case you want to disable telemetry during runtime.
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=nextjs:nodejs /app/runtime ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
