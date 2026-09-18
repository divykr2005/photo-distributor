FROM node:20-alpine AS deps
USER root
WORKDIR /app
ENV NODE_ENV=development
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps --include=dev

FROM node:20-alpine AS builder
USER root
WORKDIR /app
ENV NODE_ENV=production
ARG NEXT_PUBLIC_API_URL="https://api.snaptracer.devs.surf/api/v1"
ARG NEXT_PUBLIC_APP_URL="https://snaptracer.devs.surf"
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

USER root
RUN addgroup -g 1001 -S nodejs || true && \
    adduser -S nextjs -u 1001 -G nodejs || true

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
